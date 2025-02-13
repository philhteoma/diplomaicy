from pathlib import Path

class PromptHandler():
  _opening_prompt = ""
  _thought_reminder = ""
  _error_prompt = ""
  _order_reminder = ""

  end_thoughts = "END THOUGHTS\n"
  begin_orders = "\nBEGIN ORDERS"
  end_orders = "END ORDERS\n"
  begin_thoughts = "\nBEGIN THOUGHTS"

  def __init__(self, game, parser, power):
    self.game = game
    self.parser = parser
    self.power = power
    self.power_lower = self.power[0]+self.power[1:].lower()
    self._load_prompts()
  

  def _load_prompts(self):
    with open(Path("./prompts/opening_prompt.txt")) as file:   self._opening_prompt = file.read()
    with open(Path("./prompts/thought_reminder.txt")) as file: self._thought_reminder = file.read()
    with open(Path("./prompts/error_prompt.txt")) as file:     self._error_prompt = file.read()
    with open(Path("./prompts/order_reminder.txt")) as file:   self._order_reminder = file.read()

  def get_error_prompt(self, error_string):  
    return "\n".join([self.end_thoughts, error_string, self._error_prompt, self.begin_thoughts])

  @property
  def opening_prompt(self): 
    unit_reminder = self.parser.get_power_unit_locations(self.game, self.power)
    return "\n".join([self._opening_prompt, unit_reminder, self._thought_reminder, self.begin_thoughts])

  @property
  def thought_prompt(self):
    game_state_string = self.parser.parse_state(self.game)
    phase_intro = self.parser.get_phase_intro(self.game)

    if self._current_season in ["S", "F"]:
      unit_locations = self.parser.get_power_unit_locations(self.game, self.power).split(":")[-1].strip()
      unit_reminder = f"As {self.power}, you currently control the following units: {unit_locations}"
    elif self._current_season == "W":
      unit_reminder = self.parser.get_power_builds(self.game, self.power)
    return "\n".join([self.end_thoughts, game_state_string, phase_intro, unit_reminder, self._thought_reminder, self.begin_thoughts])
  
  
  @property
  def order_prompt(self):
    return "\n".join([self.end_thoughts, self._order_reminder, self.begin_orders])
  
  
  @property
  def _current_season(self): return self.game.current_short_phase[0]
  
