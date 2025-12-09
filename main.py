# Pico 2W Button Counter with OLED Display
# Count button presses with occasional taunting messages
#
# ==================== PINOUT ====================
#
#                    Pico 2W
#                   +-------+
#             GP0  -|  USB  |- VBUS
#             GP1  -|       |- VSYS
#             GND  -|       |- GND
#             GP2  -|       |- 3V3_EN
#             GP3  -|       |- 3V3
#    I2C SDA  GP4 <-|       |- ADC_VREF
#    I2C SCL  GP5 <-|       |- GP28
#             GND  -|       |- GND
#             GP6  -|       |- GP27
#             GP7  -|       |- GP26
#             GP8  -|       |- RUN
#             GP9  -|       |- GP22
#             GND  -|       |- GND
#            GP10  -|       |- GP21
#            GP11  -|       |- GP20
#            GP12  -|       |- GP19
#            GP13  -|       |- GP18
#            GND  -|       |- GND
#   COUNT    GP14 <-|       |- GP17
#   RESET    GP15 <-|       |- GP16
#                   +-------+
#
# WIRING:
# -------
#   OLED Display (I2C):
#     VCC  -> 3V3
#     GND  -> GND
#     SDA  -> GP4
#     SCL  -> GP5
#
#   Count Button:
#     One leg  -> GP14
#     Other    -> GND
#
#   Reset Button:
#     One leg  -> GP15
#     Other    -> GND
#
# (Buttons use internal pull-ups, active LOW)
# ===============================================

from machine import Pin, I2C
import time
import random
import json
import network
from ssd1306 import SSD1306_I2C

def connect_wifi():
    """Load WiFi credentials and connect"""
    try:
        with open("wifi.json", "r") as f:
            creds = json.load(f)

        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)

        if not wlan.isconnected():
            print(f"Connecting to {creds['ssid']}...")
            wlan.connect(creds["ssid"], creds["password"])

            # Wait for connection with timeout
            timeout = 10
            while not wlan.isconnected() and timeout > 0:
                time.sleep(1)
                timeout -= 1

        if wlan.isconnected():
            print(f"Connected! IP: {wlan.ifconfig()[0]}")
            return wlan
        else:
            print("WiFi connection failed")
            return None
    except Exception as e:
        print(f"WiFi error: {e}")
        return None


# Pin configuration
I2C_SDA = 4
I2C_SCL = 5
BTN_COUNT = 14  # Increment counter
BTN_RESET = 15  # Reset counter

# Display settings
OLED_WIDTH = 128
OLED_HEIGHT = 64

# Taunting messages - shown randomly on button press
TAUNTS = [
    "That's it?",
    "My grandma clicks faster",
    "Weak.",
    "Keep going, champ",
    "Impressive... not",
    "Is that all you got?",
    "Pathetic clicking",
    "Try harder",
    "Yawn...",
    "Are you even trying?",
    "Click like you mean it",
    "Amateur hour",
    "Sad.",
    "More! MORE!",
    "You call that clicking?",
    "I've seen better",
    "Really?",
    "Oh wow, a click",
    "Groundbreaking stuff",
    "Revolutionary clicking",
    "History in the making",
    "Alert the press",
    "Legendary...",
    "Peak performance",
    "Your finger tired yet?",
]

# Reset taunts - shown when counter is reset
RESET_TAUNTS = [
    "Giving up already?",
    "Back to zero, loser",
    "Rage quit?",
    "Starting fresh, huh?",
    "Couldn't handle it?",
    "The walk of shame",
    "Reset of defeat",
]


class ButtonCounter:
    def __init__(self):
        # Initialize I2C and display
        self.i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=400000)
        self.oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, self.i2c)

        # Initialize buttons with internal pull-up (active LOW)
        self.btn_count = Pin(BTN_COUNT, Pin.IN, Pin.PULL_UP)
        self.btn_reset = Pin(BTN_RESET, Pin.IN, Pin.PULL_UP)

        # State
        self.count = 0
        self.message = ""
        self.message_timeout = 0
        self.clicks_since_taunt = 0

        # Debounce tracking
        self.last_count_press = 0
        self.last_reset_press = 0
        self.debounce_ms = 200

        # Show initial display
        self.update_display()

    def should_show_taunt(self):
        """Determine if we should show a taunt (roughly 1 in 10 chance, but not before 5 clicks)"""
        self.clicks_since_taunt += 1
        if self.clicks_since_taunt >= 5 and random.randint(1, 10) == 1:
            self.clicks_since_taunt = 0
            return True
        return False

    def set_message(self, msg, duration_ms=2000):
        """Set a temporary message to display"""
        self.message = msg
        self.message_timeout = time.ticks_ms() + duration_ms

    def clear_message_if_expired(self):
        """Clear message if its display time has passed"""
        if self.message and time.ticks_ms() > self.message_timeout:
            self.message = ""
            self.update_display()

    def update_display(self):
        """Refresh the OLED display"""
        self.oled.fill(0)

        # Draw title
        self.oled.text("CLICK COUNTER", 10, 2, 1)

        # Draw separator line
        self.oled.hline(0, 14, 128, 1)

        # Draw count - large and centered
        count_str = str(self.count)
        # Center the count (each char is 8 pixels wide)
        x_pos = (128 - len(count_str) * 8) // 2
        self.oled.text(count_str, x_pos, 28, 1)

        # Draw message if active
        if self.message:
            # Word wrap for longer messages
            self.oled.hline(0, 46, 128, 1)
            # Truncate or wrap message to fit
            if len(self.message) <= 16:
                x_pos = (128 - len(self.message) * 8) // 2
                self.oled.text(self.message, x_pos, 52, 1)
            else:
                # Two lines for longer messages
                self.oled.text(self.message[:16], 0, 50, 1)
                self.oled.text(self.message[16:32], 0, 58, 1)

        self.oled.show()

    def handle_count_button(self):
        """Handle count button press with debounce"""
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_count_press) < self.debounce_ms:
            return

        self.last_count_press = now
        self.count += 1

        # Maybe show a taunt
        if self.should_show_taunt():
            self.set_message(random.choice(TAUNTS))

        self.update_display()

    def handle_reset_button(self):
        """Handle reset button press with debounce"""
        now = time.ticks_ms()
        if time.ticks_diff(now, self.last_reset_press) < self.debounce_ms:
            return

        self.last_reset_press = now

        if self.count > 0:
            self.count = 0
            self.clicks_since_taunt = 0
            # Always taunt on reset
            self.set_message(random.choice(RESET_TAUNTS))
            self.update_display()

    def run(self):
        """Main loop"""
        print("Button Counter started!")
        print(f"Count button: GP{BTN_COUNT}")
        print(f"Reset button: GP{BTN_RESET}")

        # Track previous button states for edge detection
        prev_count = 1
        prev_reset = 1

        while True:
            # Read current button states (0 = pressed, 1 = released)
            curr_count = self.btn_count.value()
            curr_reset = self.btn_reset.value()

            # Detect falling edge (button press)
            if prev_count == 1 and curr_count == 0:
                self.handle_count_button()

            if prev_reset == 1 and curr_reset == 0:
                self.handle_reset_button()

            # Update previous states
            prev_count = curr_count
            prev_reset = curr_reset

            # Clear expired messages
            self.clear_message_if_expired()

            # Small delay to prevent busy-waiting
            time.sleep_ms(10)


# Run the counter
if __name__ == "__main__":
    connect_wifi()
    counter = ButtonCounter()
    counter.run()
