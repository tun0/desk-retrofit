"""ESPHome external component: Slangerup desk drive.

Exposes the desk as a `cover`, so Home Assistant gets open/close/stop and
position for free. All motion control happens in a fixed-rate FreeRTOS
task in desk_cover.cpp, not in ESPHome's cooperative main loop.
"""
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import pins
from esphome.components import cover, output
from esphome.const import CONF_ID

AUTO_LOAD = ["cover"]

desk_ns = cg.esphome_ns.namespace("desk")
DeskCover = desk_ns.class_("DeskCover", cover.Cover, cg.Component)

CONF_PWM = "pwm"
CONF_RELAY_UP = "relay_up"
CONF_RELAY_DOWN = "relay_down"
CONF_WATCHDOG_PIN = "watchdog_pin"
CONF_CURRENT_PIN = "current_pin"
CONF_RAMP_UP_MS = "ramp_up_ms"
CONF_RAMP_DOWN_MS = "ramp_down_ms"
CONF_SETTLE_MS = "settle_ms"
CONF_TRAVEL_MM = "travel_mm"
CONF_SPEED_MM_S = "speed_mm_s"
CONF_MAX_RUN_MS = "max_run_ms"
CONF_STALL_A = "stall_current"

CONFIG_SCHEMA = (
    cover.COVER_SCHEMA.extend(
        {
            cv.GenerateID(): cv.declare_id(DeskCover),
            # hardware
            cv.Required(CONF_PWM): cv.use_id(output.FloatOutput),
            cv.Required(CONF_RELAY_UP): pins.gpio_output_pin_schema,
            cv.Required(CONF_RELAY_DOWN): pins.gpio_output_pin_schema,
            cv.Required(CONF_WATCHDOG_PIN): pins.gpio_output_pin_schema,
            cv.Required(CONF_CURRENT_PIN): cv.int_range(min=0, max=39),
            # motion
            cv.Optional(CONF_RAMP_UP_MS, default=500): cv.positive_int,
            cv.Optional(CONF_RAMP_DOWN_MS, default=300): cv.positive_int,
            cv.Optional(CONF_SETTLE_MS, default=50): cv.positive_int,
            cv.Optional(CONF_TRAVEL_MM, default=500): cv.positive_int,
            cv.Optional(CONF_SPEED_MM_S, default=25.0): cv.positive_float,
            # safety
            cv.Optional(CONF_MAX_RUN_MS, default=25000): cv.positive_int,
            cv.Optional(CONF_STALL_A, default=2.2): cv.positive_float,
        }
    ).extend(cv.COMPONENT_SCHEMA)
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await cover.register_cover(var, config)

    pwm = await cg.get_variable(config[CONF_PWM])
    cg.add(var.set_pwm(pwm))

    for key, setter in (
        (CONF_RELAY_UP, var.set_relay_up),
        (CONF_RELAY_DOWN, var.set_relay_down),
        (CONF_WATCHDOG_PIN, var.set_watchdog_pin),
    ):
        pin = await cg.gpio_pin_expression(config[key])
        cg.add(setter(pin))

    cg.add(var.set_current_channel(config[CONF_CURRENT_PIN]))
    cg.add(var.set_ramp_ms(config[CONF_RAMP_UP_MS],
                           config[CONF_RAMP_DOWN_MS]))
    cg.add(var.set_settle_ms(config[CONF_SETTLE_MS]))
    cg.add(var.set_geometry(config[CONF_TRAVEL_MM], config[CONF_SPEED_MM_S]))
    cg.add(var.set_limits(config[CONF_MAX_RUN_MS], config[CONF_STALL_A]))
