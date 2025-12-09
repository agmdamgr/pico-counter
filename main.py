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
#            GND   -|       |- GND
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
import urequests
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


def load_api_key():
    """Load Anthropic API key from config"""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            return config.get("anthropic_api_key", "")
    except:
        return ""


def load_high_score():
    """Load high score from file"""
    try:
        with open("highscore.json", "r") as f:
            data = json.load(f)
            return data.get("high_score", 0)
    except:
        return 0


def save_high_score(score):
    """Save high score to file"""
    try:
        with open("highscore.json", "w") as f:
            json.dump({"high_score": score}, f)
    except Exception as e:
        print(f"Error saving high score: {e}")


def fetch_ai_taunts(api_key, count=10):
    """Fetch multiple taunts from Claude API"""
    if not api_key:
        return []

    try:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }

        data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 300,
            "messages": [{
                "role": "user",
                "content": f"Generate {count} short, funny, sarcastic taunts (each under 20 chars) for someone clicking a button. One per line, no numbering, no quotes."
            }]
        }

        response = urequests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data
        )

        if response.status_code == 200:
            result = response.json()
            text = result["content"][0]["text"].strip()
            response.close()
            # Parse lines into list, filter and trim
            taunts = []
            for line in text.split("\n"):
                line = line.strip()
                if line and len(line) <= 32:
                    taunts.append(line)
            print(f"Fetched {len(taunts)} AI taunts")
            return taunts
        response.close()
        return []
    except Exception as e:
        print(f"AI taunt error: {e}")
        return []


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
    "Slow clap",
    "Do you even lift?",
    "My cat clicks better",
    "Zzzzz...",
    "Wake me when done",
    "Still going?",
    "Bless your heart",
    "A for effort",
    "Participation trophy",
    "So brave",
    "Much click. Wow.",
    "Error 404: skill",
    "Have you tried harder?",
    "Bold strategy",
    "Fascinating...",
    "Cool story bro",
    "K.",
    "Neat.",
    "Riveting stuff",
    "Edge of my seat",
    "Thrilling",
    "Stop. Don't. Come back.",
    "Oh no... anyway",
    "Press F to pay respects",
    "git gud",
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
    # 3x5 pixel patterns for digits 0-9 (each row is a 3-bit pattern)
    DIGIT_PATTERNS = {
        '0': [0b111, 0b101, 0b101, 0b101, 0b111],
        '1': [0b010, 0b110, 0b010, 0b010, 0b111],
        '2': [0b111, 0b001, 0b111, 0b100, 0b111],
        '3': [0b111, 0b001, 0b111, 0b001, 0b111],
        '4': [0b101, 0b101, 0b111, 0b001, 0b001],
        '5': [0b111, 0b100, 0b111, 0b001, 0b111],
        '6': [0b111, 0b100, 0b111, 0b101, 0b111],
        '7': [0b111, 0b001, 0b001, 0b001, 0b001],
        '8': [0b111, 0b101, 0b111, 0b101, 0b111],
        '9': [0b111, 0b101, 0b111, 0b001, 0b111],
    }

    def __init__(self):
        # Initialize I2C and display
        self.i2c = I2C(0, sda=Pin(I2C_SDA), scl=Pin(I2C_SCL), freq=400000)
        self.oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, self.i2c)

        # Initialize buttons with internal pull-up (active LOW)
        self.btn_count = Pin(BTN_COUNT, Pin.IN, Pin.PULL_UP)
        self.btn_reset = Pin(BTN_RESET, Pin.IN, Pin.PULL_UP)

        # State
        self.count = 0
        self.high_score = load_high_score()
        self.record_broken = False  # Track if we've broken record this session
        self.message = ""
        self.message_timeout = 0
        self.clicks_since_taunt = 0

        # AI taunt state
        self.api_key = load_api_key()
        self.ai_taunt_cache = []
        self.taunts_since_ai = 0

        # Confetti state
        self.confetti_particles = []
        self.last_confetti_update = 0

        # Debounce tracking
        self.last_count_press = 0
        self.last_reset_press = 0
        self.debounce_ms = 200

        # Show initial display
        self.update_display()

    def should_show_taunt(self):
        """Determine if we should show a taunt (roughly 1 in 15 chance, but not before 10 clicks)"""
        self.clicks_since_taunt += 1
        if self.clicks_since_taunt >= 10 and random.randint(1, 15) == 1:
            self.clicks_since_taunt = 0
            return True
        return False

    def get_taunt(self):
        """Get a taunt - occasionally from AI cache if available"""
        self.taunts_since_ai += 1
        # Try AI taunt every 3rd taunt if API key is available
        if self.api_key and self.taunts_since_ai >= 3:
            self.taunts_since_ai = 0
            # Refill cache if empty
            if not self.ai_taunt_cache:
                print("Fetching new AI taunts...")
                self.ai_taunt_cache = fetch_ai_taunts(self.api_key, 10)
                print(f"Cache now has {len(self.ai_taunt_cache)} taunts")
            # Pop from cache if available
            if self.ai_taunt_cache:
                taunt = self.ai_taunt_cache.pop()
                print(f"[AI] {taunt}")
                return taunt
        taunt = random.choice(TAUNTS)
        print(f"[Local] {taunt}")
        return taunt

    def draw_large_digit(self, digit, x, y, scale=3):
        """Draw a digit at scale (default 3x makes 9x15 pixel digits)"""
        if digit not in self.DIGIT_PATTERNS:
            return 0
        pattern = self.DIGIT_PATTERNS[digit]
        for row_idx, row in enumerate(pattern):
            for col in range(3):
                if row & (1 << (2 - col)):
                    self.oled.fill_rect(x + col * scale, y + row_idx * scale, scale, scale, 1)
        return 3 * scale + 2  # Return width + spacing

    def draw_large_number(self, num, y):
        """Draw a number centered on screen"""
        num_str = str(num)
        digit_width = 3 * 3 + 2  # 3 pixels * scale 3 + 2 spacing
        total_width = len(num_str) * digit_width - 2  # Remove last spacing
        x = (128 - total_width) // 2
        for digit in num_str:
            x += self.draw_large_digit(digit, x, y)

    def start_confetti(self):
        """Start a confetti animation for milestone counts"""
        self.confetti_particles = []
        for _ in range(15):
            self.confetti_particles.append({
                'x': random.randint(0, 127),
                'y': random.randint(-30, 0),
                'speed': random.randint(3, 6),
                'drift': random.randint(-1, 1)
            })
        self.last_confetti_update = time.ticks_ms()

    def explosion_animation(self, score):
        """Animate the score exploding outward"""
        # Create digit particles with velocities
        num_str = str(score) if score > 0 else "0"
        digit_width = 3 * 3 + 2
        total_width = len(num_str) * digit_width - 2
        start_x = (128 - total_width) // 2

        # Create particles for each digit
        particles = []
        x = start_x
        for digit in num_str:
            # Give each digit a random velocity
            speed = random.randint(4, 8)
            particles.append({
                'digit': digit,
                'x': x,
                'y': 24,  # Starting y position
                'vx': speed * (1 if random.randint(0, 1) else -1) * random.random(),
                'vy': -speed + random.randint(-2, 2),
                'rot': 0,
                'scale': 3
            })
            x += digit_width

        # Animate for about 1 second
        frames = 20
        for frame in range(frames):
            self.oled.fill(0)
            self.oled.text("CLICK COUNTER", 10, 2, 1)
            self.oled.hline(0, 14, 128, 1)

            # Update and draw each digit particle
            for p in particles:
                # Apply gravity
                p['vy'] += 0.8
                p['x'] += p['vx']
                p['y'] += p['vy']

                # Add some spin by reducing scale over time
                if frame > frames // 2:
                    p['scale'] = max(1, p['scale'] - 0.3)

                # Draw digit if on screen
                if -20 <= p['x'] <= 140 and -20 <= p['y'] <= 80:
                    self.draw_large_digit(p['digit'], int(p['x']), int(p['y']), max(1, int(p['scale'])))

            # Add some explosion sparks
            if frame < 8:
                for _ in range(5):
                    sx = 64 + random.randint(-30, 30)
                    sy = 30 + random.randint(-15, 15)
                    if 0 <= sx < 128 and 0 <= sy < 64:
                        self.oled.pixel(sx, sy, 1)

            self.oled.show()
            time.sleep_ms(50)

        # Brief pause showing empty
        self.oled.fill(0)
        self.oled.text("CLICK COUNTER", 10, 2, 1)
        self.oled.hline(0, 14, 128, 1)
        self.oled.text("BOOM!", 44, 35, 1)
        self.oled.show()
        time.sleep_ms(500)

    def update_confetti(self):
        """Update confetti particles, returns True if animation still active"""
        if not self.confetti_particles:
            return False

        now = time.ticks_ms()
        # Update at ~20fps (every 50ms)
        if time.ticks_diff(now, self.last_confetti_update) < 50:
            return True

        self.last_confetti_update = now

        # Update particle positions and remove those off-screen
        active = []
        for p in self.confetti_particles:
            p['y'] += p['speed']
            p['x'] += p['drift']
            if p['y'] < 70:  # Keep if still visible
                active.append(p)
        self.confetti_particles = active
        return len(active) > 0

    def set_message(self, msg, duration_ms=4000):
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
        self.draw_large_number(self.count, 24)

        # Draw confetti particles
        for p in self.confetti_particles:
            if 0 <= p['y'] < 64 and 0 <= p['x'] < 128:
                self.oled.fill_rect(int(p['x']), int(p['y']), 3, 2, 1)

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

        # Check for new high score
        if self.count > self.high_score:
            if not self.record_broken:
                # Just broke the record for first time this session!
                self.record_broken = True
                self.set_message("NEW RECORD!")
                self.start_confetti()
                print(f"New high score: {self.count}")
            else:
                # Already broke record, continue normal behavior
                if self.count > 0 and self.count % 100 == 0:
                    self.start_confetti()
                elif self.should_show_taunt():
                    self.set_message(self.get_taunt())
            self.high_score = self.count
            save_high_score(self.high_score)
        # Check for milestone (every 100)
        elif self.count > 0 and self.count % 100 == 0:
            self.start_confetti()
        # Maybe show a taunt
        elif self.should_show_taunt():
            self.set_message(self.get_taunt())

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
            self.record_broken = False  # Reset so we can celebrate again
            # Always taunt on reset
            self.set_message(random.choice(RESET_TAUNTS))
            self.update_display()

    def show_stats_screen(self):
        """Display high score stats screen"""
        self.oled.fill(0)
        self.oled.text("HIGH SCORE", 24, 2, 1)
        self.oled.hline(0, 14, 128, 1)
        self.draw_large_number(self.high_score, 28)
        self.oled.show()

    def reset_high_score(self):
        """Secret reset of high score with explosion animation"""
        print(f"SECRET RESET! Destroying high score: {self.high_score}")
        old_score = self.high_score
        self.explosion_animation(old_score)
        self.high_score = 0
        self.count = 0
        self.record_broken = False
        self.clicks_since_taunt = 0
        save_high_score(0)
        self.set_message("Score destroyed!")
        self.update_display()

    def run(self):
        """Main loop"""
        print("Button Counter started!")
        print(f"Count button: GP{BTN_COUNT}")
        print(f"Reset button: GP{BTN_RESET}")
        print(f"High score: {self.high_score}")

        # Track previous button states for edge detection
        prev_count = 1
        prev_reset = 1

        # Track reset button hold time
        reset_press_start = 0
        showing_stats = False
        hold_threshold_ms = 1000  # 1 second hold

        # Track both buttons held for secret reset
        both_pressed_start = 0
        secret_reset_threshold_ms = 3000  # 3 seconds
        secret_reset_triggered = False

        while True:
            # Read current button states (0 = pressed, 1 = released)
            curr_count = self.btn_count.value()
            curr_reset = self.btn_reset.value()

            # Check for both buttons held (secret high score reset)
            both_pressed = (curr_count == 0 and curr_reset == 0)

            if both_pressed:
                if both_pressed_start == 0:
                    both_pressed_start = time.ticks_ms()
                elif not secret_reset_triggered:
                    if time.ticks_diff(time.ticks_ms(), both_pressed_start) >= secret_reset_threshold_ms:
                        # Secret reset triggered!
                        secret_reset_triggered = True
                        self.reset_high_score()
            else:
                both_pressed_start = 0
                secret_reset_triggered = False

            # Skip normal button handling if both are pressed (secret combo)
            if both_pressed:
                prev_count = curr_count
                prev_reset = curr_reset
                time.sleep_ms(10)
                continue

            # Detect falling edge (button press)
            if prev_count == 1 and curr_count == 0:
                self.handle_count_button()

            # Reset button: track hold time
            if prev_reset == 1 and curr_reset == 0:
                # Button just pressed
                reset_press_start = time.ticks_ms()

            if curr_reset == 0 and reset_press_start > 0:
                # Button held - check if past threshold
                if time.ticks_diff(time.ticks_ms(), reset_press_start) >= hold_threshold_ms:
                    if not showing_stats:
                        self.show_stats_screen()
                        showing_stats = True

            if prev_reset == 0 and curr_reset == 1:
                # Button just released
                if showing_stats:
                    # Was showing stats, just restore display
                    self.update_display()
                    showing_stats = False
                elif time.ticks_diff(time.ticks_ms(), reset_press_start) < hold_threshold_ms:
                    # Short press - do reset
                    self.handle_reset_button()
                reset_press_start = 0

            # Update previous states
            prev_count = curr_count
            prev_reset = curr_reset

            # Clear expired messages
            self.clear_message_if_expired()

            # Update confetti animation
            if self.update_confetti():
                self.update_display()

            # Small delay to prevent busy-waiting
            time.sleep_ms(10)


# Run the counter
if __name__ == "__main__":
    connect_wifi()
    counter = ButtonCounter()
    counter.run()
