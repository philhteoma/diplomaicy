from diplomacy import Game

class StateParser():
  HEADER = "CURRENT GAME STATE\n\n"

  ORDERS_SECTION_TITLE = "PREVIOUS PHASE ORDERS:"
  UNITS_SECTION_TITLE = "CURRENT UNIT LOCATIONS:"
  SUPPLY_SECTION_TITLE = "CURRENT CONTROLLED SUPPLY CENTERS:"

  SECTION_SEP = "\n\n"
  
  POWER_SUFFIX = ": "

  RESULT_SEP = " -> "
  TITLE_SEP = "\n"
  POWER_SEP = "\n"
  ITEM_SEP = ", "
  
  MOVEMENT_PHASE_REMINDER = "This is a movement phase - you will be provding movement, support or convoy orders for your units."
  RETREAT_PHASE_REMINDER = "This is a retreat phase - if you have armies that need need to retreat, you will need to provide destiations for them."
  ADJUSTMENT_PHASE_REMINDER = "This is an adjustment phase - you will be providing orders to build or disband units."

  PHASE_REMINDER_MAP = {
    "M" : MOVEMENT_PHASE_REMINDER,
    "R" : RETREAT_PHASE_REMINDER,
    "A" : ADJUSTMENT_PHASE_REMINDER,
  }


  PHASE_CODES = {
    "S" : "Spring",
    "F" : "Fall",
    "W" : "Winter",
    "M" : "Movement",
    "R" : "Retreat",
    "A" : "Adjustment",
  }

  def init(self):
    return self
  
  def get_long_phase_name(self, short_phase:str) -> str:
    return self.PHASE_CODES[short_phase[0]] + " " + short_phase[1:-1] + " " + self.PHASE_CODES[short_phase[-1]]

  def get_phase_intro(self, game):
    phase_type = game.current_short_phase[-1]
    long_name = self.get_long_phase_name(game.current_short_phase)

    return long_name + "\n" + self.PHASE_REMINDER_MAP[phase_type]

  def get_power_unit_locations(self, game:dict, power:str):
    units = game.get_state()["units"][power]
    return self.UNITS_SECTION_TITLE + self.POWER_SUFFIX + self.ITEM_SEP.join(units)

  def parse_state(self, game: Game):
    state = game.get_state()

    state_str =  self.HEADER
    state_str += self._parse_orders(game.get_phase_history()[-1].orders, game.get_phase_history()[-1].results)
    state_str += self.SECTION_SEP
    state_str += self._parse_unit_locations(state["units"])
    state_str += self.SECTION_SEP
    state_str += self._parse_controlled_centers(state["centers"])

    return state_str


  def _parse_unit_locations(self, units_state: dict) -> str:
    return self._build_phrase(self.UNITS_SECTION_TITLE, units_state)
  

  def _parse_controlled_centers(self, centers_state:dict) -> str:
    return self._build_phrase(self.SUPPLY_SECTION_TITLE, centers_state)
  

  def _build_phrase(self, title:str, info: dict) -> str:
    title += self.TITLE_SEP
    for power, items in info.items():
      title += power
      title += self.POWER_SUFFIX
      title += self.ITEM_SEP.join(items)
      title += self.POWER_SEP
    
    return title
  

  def _parse_orders(self, orders: dict, results: dict):
    for power, power_orders in orders.items():   # For each Power
      for i, power_order in enumerate(power_orders): # For each order that power made
        for r_order, result in results.items(): # For each result
          if r_order == power_order[:5]: # If the result order matches the target order
            power_orders[i] = self._append_result(power_order, result)
            break
    
    return self.ORDERS_SECTION_TITLE + self.TITLE_SEP + self._unpack_orders(orders)
  
  
  def _append_result(self, order, result):
      if len(result) == 0: unpacked_result = "SUCCESS"
      else: 
        unpacked_result = str(result)
        if "bounce" in unpacked_result: 
          unpacked_result = "FAILED - BOUNCE"
        elif "no convoy" in unpacked_result:
          unpacked_result = "FAILED - NO CONVOY"
        elif ("0:" in unpacked_result) and (order[-2:] == " B"):
          unpacked_result = "SUCCESS"
        elif ("void" in unpacked_result) and (" S " in order): 
          unpacked_result = "SUPPORT"
        elif ("void" in unpacked_result) and (" C " in order): 
          unpacked_result = "CONVOY"
        else: 
          unpacked_result = "UNKNOWN"
      
      return order + self.RESULT_SEP + unpacked_result
  

  def _unpack_orders(self, orders: dict):
    unpack_logic = lambda power, orders:[(power, order) for order in orders]
    return self.POWER_SEP.join([f"{order[0]}{self.POWER_SUFFIX}{order[1]}" 
            for power, orders in orders.items() 
            for order in unpack_logic(power, orders)])
      



  