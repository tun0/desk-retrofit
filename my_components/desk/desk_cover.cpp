#include "desk_cover.h"

#include "esphome/core/log.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

namespace esphome {
namespace desk {

static const char *const TAG = "desk";

void DeskCover::setup() {
  this->relay_up_->setup();
  this->relay_down_->setup();
  this->wdt_pin_->setup();
  this->setup_adc_();

  this->apply_relays_(Dir::NONE);
  this->set_duty_(0.0f);
  this->enter_(DeskState::IDLE);

  this->position = 0.0f;
  this->current_operation = cover::COVER_OPERATION_IDLE;
  this->publish_state(false);

  // Core 0: the control loop must not share a core with the WiFi stack,
  // or a reconnect can stall a tick by hundreds of milliseconds.
  xTaskCreatePinnedToCore(&DeskCover::task_trampoline_, "desk_ctl", 4096,
                          this, configMAX_PRIORITIES - 3, nullptr, 0);
}

void DeskCover::task_trampoline_(void *arg) {
  static_cast<DeskCover *>(arg)->control_loop_();
}

void DeskCover::control_loop_() {
  TickType_t last = xTaskGetTickCount();
  for (;;) {
    this->tick_();

    // Kick AFTER a complete iteration, never on a timer. A hardware PWM
    // or an RTOS-driven pulse would keep kicking through a wedged loop
    // and the external monostable would protect nothing.
    this->wdt_level_ = !this->wdt_level_;
    this->wdt_pin_->digital_write(this->wdt_level_);

    vTaskDelayUntil(&last, pdMS_TO_TICKS(TICK_MS));
  }
}

void DeskCover::tick_() {
  const uint32_t now = millis();
  const uint32_t in_state = now - this->state_entered_ms_;
  const float amps = this->read_current_();
  this->amps_.store(amps);

  // Dead reckoning. Phase 2 replaces this with the ToF reading.
  if (this->state_.load() == DeskState::RUNNING ||
      this->state_.load() == DeskState::RAMPING ||
      this->state_.load() == DeskState::STOPPING) {
    const float dt = TICK_MS / 1000.0f;
    const float step = this->speed_mm_s_ * this->duty_ * dt *
                       static_cast<float>(this->dir_);
    this->position_mm_.store(this->position_mm_.load() + step);
  }

  const int8_t req = this->request_.load();

  switch (this->state_.load()) {
    case DeskState::IDLE: {
      if (req != 0) {
        this->dir_ = req > 0 ? Dir::UP : Dir::DOWN;
        this->set_duty_(0.0f);
        this->apply_relays_(this->dir_);
        this->move_started_ms_ = now;
        this->enter_(DeskState::SETTLING);
      }
      break;
    }

    case DeskState::SETTLING: {
      // Contacts have moved; give them time to stop bouncing before any
      // current flows through them.
      if (in_state >= this->settle_ms_)
        this->enter_(DeskState::RAMPING);
      break;
    }

    case DeskState::RAMPING: {
      if (req == 0 || req != static_cast<int8_t>(this->dir_)) {
        this->enter_(DeskState::STOPPING);
        break;
      }
      const float f = static_cast<float>(in_state) / this->ramp_up_ms_;
      this->set_duty_(f >= 1.0f ? 1.0f : f);
      if (f >= 1.0f)
        this->enter_(DeskState::RUNNING);
      break;
    }

    case DeskState::RUNNING: {
      if (req == 0 || req != static_cast<int8_t>(this->dir_)) {
        this->enter_(DeskState::STOPPING);
        break;
      }
      // Current collapsing to zero means a limit switch opened. That is a
      // normal, repeatable mechanical reference, not a fault.
      if (amps < 0.10f) {
        ESP_LOGI(TAG, "limit reached (current collapsed)");
        if (this->dir_ == Dir::DOWN) {
          this->position_mm_.store(0.0f);
          this->homed_.store(true);
        } else {
          this->position_mm_.store(static_cast<float>(this->travel_mm_));
        }
        this->request_.store(0);
        this->enter_(DeskState::STOPPING);
        break;
      }
      if (amps > this->stall_a_) {
        this->fault_("overcurrent / obstruction");
        break;
      }
      if (now - this->move_started_ms_ > this->max_run_ms_) {
        this->fault_("travel timeout");
        break;
      }
      break;
    }

    case DeskState::STOPPING: {
      const float f = 1.0f - static_cast<float>(in_state) /
                                 this->ramp_down_ms_;
      this->set_duty_(f <= 0.0f ? 0.0f : f);
      if (f <= 0.0f) {
        // Release relays only once the FET is off and current has decayed.
        this->apply_relays_(Dir::NONE);
        this->dir_ = Dir::NONE;
        this->enter_(DeskState::IDLE);
      }
      break;
    }

    case DeskState::FAULT: {
      this->set_duty_(0.0f);
      this->apply_relays_(Dir::NONE);
      break;
    }
  }
}

void DeskCover::apply_relays_(Dir d) {
  this->relay_up_->digital_write(d == Dir::UP);
  this->relay_down_->digital_write(d == Dir::DOWN);
}

void DeskCover::set_duty_(float duty) {
  this->duty_ = duty;
  if (this->pwm_ != nullptr)
    this->pwm_->set_level(duty);
}

void DeskCover::setup_adc_() {
  // adc_channel_ actually holds a GPIO number (see cover.py's current_pin
  // schema) - resolve it to an ADC1 channel here rather than in every
  // read_current_() call. ESP32-S3 ADC1: channels 0-9 map to GPIO1-10, in
  // order - this table does not carry over to the classic ESP32 or other
  // targets, since ADC channel-to-GPIO mapping is chip-specific.
  if (this->adc_channel_ < 1 || this->adc_channel_ > 10) {
    ESP_LOGE(TAG, "current_pin %u is not a valid ADC1 GPIO on the S3 (1-10)",
              this->adc_channel_);
    return;
  }
  const uint8_t ch_index = this->adc_channel_ - 1;

#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0)
  this->adc_ch_ = static_cast<adc_channel_t>(ch_index);

  adc_oneshot_unit_init_cfg_t unit_cfg = {};
  unit_cfg.unit_id = ADC_UNIT_1;
  if (adc_oneshot_new_unit(&unit_cfg, &this->adc_unit_) != ESP_OK) {
    ESP_LOGE(TAG, "adc_oneshot_new_unit failed");
    return;
  }

  adc_oneshot_chan_cfg_t chan_cfg = {};
  chan_cfg.bitwidth = ADC_BITWIDTH_DEFAULT;
  chan_cfg.atten = ADC_ATTEN_DB_12;  // ~0-3.3V full scale
  adc_oneshot_config_channel(this->adc_unit_, this->adc_ch_, &chan_cfg);

  adc_cali_curve_fitting_config_t cali_cfg = {};
  cali_cfg.unit_id = ADC_UNIT_1;
  cali_cfg.chan = this->adc_ch_;
  cali_cfg.atten = ADC_ATTEN_DB_12;
  cali_cfg.bitwidth = ADC_BITWIDTH_DEFAULT;
  this->adc_calibrated_ =
      adc_cali_create_scheme_curve_fitting(&cali_cfg, &this->adc_cali_) ==
      ESP_OK;
#else
  this->adc_ch_ = static_cast<adc1_channel_t>(ch_index);
  adc1_config_width(ADC_WIDTH_BIT_12);
  adc1_config_channel_atten(this->adc_ch_, ADC_ATTEN_DB_11);
  esp_adc_cal_characterize(ADC_UNIT_1, ADC_ATTEN_DB_11, ADC_WIDTH_BIT_12,
                           1100, &this->adc_cal_);
  this->adc_calibrated_ = true;
#endif

  if (!this->adc_calibrated_)
    ESP_LOGW(TAG, "ADC calibration unavailable - falling back to an "
                  "uncalibrated raw-count estimate");
}

float DeskCover::read_current_() {
  int raw = 0;
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0)
  if (this->adc_unit_ == nullptr ||
      adc_oneshot_read(this->adc_unit_, this->adc_ch_, &raw) != ESP_OK)
    return this->amps_.load();
#else
  raw = adc1_get_raw(this->adc_ch_);
#endif

  int mv;
  if (this->adc_calibrated_) {
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0)
    adc_cali_raw_to_voltage(this->adc_cali_, raw, &mv);
#else
    mv = static_cast<int>(esp_adc_cal_raw_to_voltage(raw, &this->adc_cal_));
#endif
  } else {
    // Uncalibrated fallback: 12-bit reading over a ~3.3V full-scale span.
    // Less accurate than the calibrated path, but keeps the loop running
    // rather than faulting on a chip without eFuse calibration data.
    mv = static_cast<int>(raw * 3300.0f / 4095.0f);
  }

  // Undo the R1(10k)/R2(20k) divider, then the ACS712ELCTR-05B's own 2.5V
  // bias and 185mV/A sensitivity (Allegro's datasheet figure, see README
  // §4.4) - this part's transfer function really is linear over its full
  // range, not a lookup table.
  const float sensor_mv = mv * (10.0f + 20.0f) / 20.0f;
  return (sensor_mv - 2500.0f) / 185.0f;
}

void DeskCover::enter_(DeskState s) {
  this->state_.store(s);
  this->state_entered_ms_ = millis();
}

void DeskCover::fault_(const char *why) {
  this->fault_reason_ = why;
  this->set_duty_(0.0f);
  this->apply_relays_(Dir::NONE);
  this->request_.store(0);
  this->enter_(DeskState::FAULT);
}

// ---------------------------------------------------------------------
// ESPHome main loop: UI and Home Assistant only. No motion decisions here.
// ---------------------------------------------------------------------
void DeskCover::loop() {
  const float pos_mm = this->position_mm_.load();
  const float pos = pos_mm / static_cast<float>(this->travel_mm_);
  const DeskState st = this->state_.load();

  auto op = cover::COVER_OPERATION_IDLE;
  if (st == DeskState::RAMPING || st == DeskState::RUNNING ||
      st == DeskState::STOPPING)
    op = this->dir_ == Dir::UP ? cover::COVER_OPERATION_OPENING
                               : cover::COVER_OPERATION_CLOSING;

  if (std::abs(pos - this->position) > 0.005f ||
      op != this->current_operation) {
    this->position = pos < 0.0f ? 0.0f : (pos > 1.0f ? 1.0f : pos);
    this->current_operation = op;
    this->publish_state(false);
  }

  // Closed-loop hold toward a requested position, once homed.
  const float target = this->target_mm_.load();
  if (target >= 0.0f && st == DeskState::IDLE) {
    const float err = target - pos_mm;
    if (std::abs(err) > 3.0f)
      this->request_.store(err > 0 ? 1 : -1);
    else
      this->target_mm_.store(-1.0f);
  }
}

cover::CoverTraits DeskCover::get_traits() {
  auto traits = cover::CoverTraits();
  traits.set_supports_position(true);
  traits.set_supports_stop(true);
  traits.set_is_assumed_state(false);
  return traits;
}

void DeskCover::control(const cover::CoverCall &call) {
  if (call.get_stop()) {
    this->target_mm_.store(-1.0f);
    this->request_.store(0);
  }
  if (call.get_position().has_value()) {
    const float want = *call.get_position();
    this->target_mm_.store(want * static_cast<float>(this->travel_mm_));
  }
}

void DeskCover::dump_config() {
  ESP_LOGCONFIG(TAG, "Desk cover:");
  ESP_LOGCONFIG(TAG, "  tick %u Hz, ramp %u/%u ms, settle %u ms",
                TICK_HZ, this->ramp_up_ms_, this->ramp_down_ms_,
                this->settle_ms_);
  ESP_LOGCONFIG(TAG, "  travel %u mm at %.1f mm/s, max run %u ms",
                this->travel_mm_, this->speed_mm_s_, this->max_run_ms_);
  LOG_PIN("  Relay up: ", this->relay_up_);
  LOG_PIN("  Relay down: ", this->relay_down_);
  LOG_PIN("  Watchdog: ", this->wdt_pin_);
}

}  // namespace desk
}  // namespace esphome
