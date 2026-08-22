#pragma once

#include <atomic>

#include "esphome/core/component.h"
#include "esphome/core/hal.h"
#include "esphome/components/cover/cover.h"
#include "esphome/components/output/float_output.h"

#include "esp_idf_version.h"
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0)
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#else
#include "driver/adc.h"
#include "esp_adc_cal.h"
#endif

namespace esphome {
namespace desk {

// Motion is legal only in specific states. Relay writes are permitted in
// IDLE alone; everything else must go through SETTLING first. Making that
// structural is what stops a later refactor switching a relay under load.
enum class DeskState : uint8_t {
  IDLE,      // relays released, FET off, desk braked
  SETTLING,  // direction chosen, waiting for current to decay
  RAMPING,   // PWM climbing to full
  RUNNING,   // at speed
  STOPPING,  // PWM falling
  FAULT,     // latched; requires an explicit clear
};

enum class Dir : int8_t { NONE = 0, UP = 1, DOWN = -1 };

class DeskCover : public cover::Cover, public Component {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::LATE; }

  cover::CoverTraits get_traits() override;
  void control(const cover::CoverCall &call) override;

  void set_pwm(output::FloatOutput *pwm) { this->pwm_ = pwm; }
  void set_relay_up(GPIOPin *p) { this->relay_up_ = p; }
  void set_relay_down(GPIOPin *p) { this->relay_down_ = p; }
  void set_watchdog_pin(GPIOPin *p) { this->wdt_pin_ = p; }
  void set_current_channel(uint8_t ch) { this->adc_channel_ = ch; }
  void set_ramp_ms(uint32_t up, uint32_t down) {
    this->ramp_up_ms_ = up;
    this->ramp_down_ms_ = down;
  }
  void set_settle_ms(uint32_t ms) { this->settle_ms_ = ms; }
  void set_geometry(uint32_t travel_mm, float speed_mm_s) {
    this->travel_mm_ = travel_mm;
    this->speed_mm_s_ = speed_mm_s;
  }
  void set_limits(uint32_t max_run_ms, float stall_a) {
    this->max_run_ms_ = max_run_ms;
    this->stall_a_ = stall_a;
  }

  // Telemetry for the YAML side (sensors, display, logging).
  float current_amps() const { return this->amps_.load(); }
  uint8_t state_id() const {
    return static_cast<uint8_t>(this->state_.load());
  }

 protected:
  static void task_trampoline_(void *arg);
  void control_loop_();      // runs at TICK_HZ on its own core
  void tick_();              // one iteration of the state machine
  void apply_relays_(Dir d);
  void set_duty_(float duty);
  void setup_adc_();
  float read_current_();
  void enter_(DeskState s);
  void fault_(const char *why);

  static constexpr uint32_t TICK_HZ = 200;
  static constexpr uint32_t TICK_MS = 1000 / TICK_HZ;

  output::FloatOutput *pwm_{nullptr};
  GPIOPin *relay_up_{nullptr};
  GPIOPin *relay_down_{nullptr};
  GPIOPin *wdt_pin_{nullptr};
  uint8_t adc_channel_{0};  // GPIO number (see cover.py); resolved to an
                            // ADC1 channel enum in setup_adc_(), not itself
                            // a channel index
#if ESP_IDF_VERSION >= ESP_IDF_VERSION_VAL(5, 0, 0)
  adc_oneshot_unit_handle_t adc_unit_{nullptr};
  adc_cali_handle_t adc_cali_{nullptr};
  adc_channel_t adc_ch_{ADC_CHANNEL_0};
#else
  esp_adc_cal_characteristics_t adc_cal_{};
  adc1_channel_t adc_ch_{ADC1_CHANNEL_0};
#endif
  bool adc_calibrated_{false};

  uint32_t ramp_up_ms_{500}, ramp_down_ms_{300}, settle_ms_{50};
  uint32_t travel_mm_{500}, max_run_ms_{25000};
  float speed_mm_s_{25.0f}, stall_a_{2.2f};

  // Written by the control task, read by the ESPHome loop.
  std::atomic<DeskState> state_{DeskState::IDLE};
  std::atomic<float> amps_{0.0f};
  std::atomic<float> position_mm_{0.0f};
  std::atomic<bool> homed_{false};

  // Written by the ESPHome loop, read by the control task.
  std::atomic<float> target_mm_{-1.0f};   // <0 means "no target"
  std::atomic<int8_t> request_{0};        // +1 up, -1 down, 0 stop

  Dir dir_{Dir::NONE};
  float duty_{0.0f};
  uint32_t state_entered_ms_{0};
  uint32_t move_started_ms_{0};
  bool wdt_level_{false};
  const char *fault_reason_{nullptr};
};

}  // namespace desk
}  // namespace esphome
