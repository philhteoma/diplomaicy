import string

from diplomacy import Game
import diplomacy.utils.errors as err

class Footer():
  unit_reminder = False
  order_thought_reminder = False

class MoveChecker():
  MALFORMED_ORDER_ERROR = "ORDERS ARE NOT IN THE CORRECT FORMAT"

  NO_ARMY_ERROR = " has no army in "
  NO_FLEET_ERROR = " has no fleet in "

  UNIT_REMINDER = " has the following units: "

  MISTAKE_REMINDER = "You should now write a sentence on what went wrong, and how you will fix it. Keep this brief, and do not include any orders in standard diplomacy notation.\n"

  VALID_CHARACTERS = list(string.ascii_uppercase+"/- \n")

  def __init__(self, game: Game, parser, check_convoy_path=True):
    self.game = game
    self.map = game.map
    self.parser = parser

    self.check_convoy = check_convoy_path

    self.all_locs = [x.upper() for x in game.map.locs]
    self.map_loc_type = {loc.upper(): t for loc, t in self.map.loc_type.items()}
    self.sea_territories = [loc.upper() for loc, t in self.map_loc_type.items() if t == "WATER"]

    
  def check_all_orders(self, power, response_text: str):
    footer = Footer()
    result, invalid_orders = self.check_moves(power, response_text, footer)

    if not result:
      e_string = "END ORDERS\n\nINVALID ORDERS:\n"
      e_string += "\n".join([f"{order}: {error}" for order, error in invalid_orders])
      r, e_string = True, e_string
    else:
      r, e_string = False, ""
    
    if footer.unit_reminder: e_string += "+\n" + self.parser.get_power_unit_locations(self.game, power) + "\n"
    if footer.order_thought_reminder: e_string += "+\n" + "You may be submitting your thoughts as orders. Remember, after the command \"SUBMIT ORDERS\", you must *only* submit orders in standard diplomacy notation."
    
    e_string += "\n" + self.MISTAKE_REMINDER
    e_string += "\nBEGIN THOUGHTS\n"

    return r, e_string

  def check_moves(self, power, response_text: str, footer: Footer):
    invalid_orders = []
    orders = response_text.split("\n")
    orders = [order.strip() for order in orders if order != ""]

    # Get some relevant data from game state
    self.all_units = [x for y in self.game.get_state()["units"].values() for x in y] # List of all units in the game
    self.build_counts = self.game.get_state()["builds"][power]["count"]
    self.total_units = len(self.game.get_state()["units"][power])

    self.order_count = len(orders)

    # Is the LLM submitting its thoughts as orders?
    if any([len(order) > 30 for order in orders]):
      footer.order_thought_reminder = True

    if self.game.current_short_phase[0] in ["S", "F"]:
      if self.order_count > self.total_units:
        return False, [("", f"You submitted {self.order_count} orders, but you only have {self.total_units} units")]
      if self.order_count < self.build_counts:
        return False, [("", f"You submitted {self.order_count} orders, but you have {self.build_counts} units")]
    elif self.game.current_short_phase[0] == "W":
      if self.order_count > self.build_counts:
        return False, [("", f"You submitted {self.order_count} orders, but you only have {self.build_counts} builds")]
      if self.order_count < self.build_counts:
        return False, [("", f"You submitted {self.order_count} orders, but you have {self.build_counts} builds")]


    # If no orders, return True
    if not orders: return True

    # Any character in order is not in A-Z/-
    if any([c.islower() for c in response_text]): return False, [("Uppercase: ", "All characters must be uppercase")]

    invalid_characters = [c for c in response_text if c not in self.VALID_CHARACTERS]
    if any([c not in self.VALID_CHARACTERS for c in response_text]): return False, [("Non-letter: ",self.MALFORMED_ORDER_ERROR)]
    

    # Sanity checks for entire order list
    for order in orders:
      # Any word in any order is longer than 3 characters
      if any([len(x) > 3 for x in order.split(" ")]): return False, [("Words too long: ",self.MALFORMED_ORDER_ERROR)]

    
    # Generic checks
    for order in orders:
      valid, msg = self._generic_check(order, power, footer)
      if not valid: invalid_orders.append((order, "GENERIC ERROR: " + msg))
  

    # Only look at orders not yet marked invalid
    orders = [order for order in orders if order not in [x[0] for x in invalid_orders]]

    convoy_orders = [order for order in orders if " C " in order]
    support_orders = [order for order in orders if " S " in order]
    hold_orders = [order for order in orders if order[-2:] == " H"]
    build_orders = [order for order in orders if order[-2:] == " B"]
    # All other orders treated as move orders
    move_orders = [order for order in orders if order not in convoy_orders + support_orders + build_orders + hold_orders]

    # Convoy checks
    for order in convoy_orders:
      valid, msg = self._convoy_check(order, power, footer)
      if not valid: invalid_orders.append((order, "ORDER ERROR: " + msg))

    # Support checks
    for order in support_orders:
      valid, msg = self._support_check(order, power, footer)
      if not valid: invalid_orders.append((order, "SUPPORT ERROR: " + msg))

    # Movement checks
    for order in move_orders:
      valid, msg = self._move_check(order, power, convoy_orders, invalid_orders,footer)
      if not valid: invalid_orders.append((order, "MOVE ERROR: " + msg))
    
    # Hold checks
    for order in hold_orders:
      valid, msg = self._hold_check(order, power, footer)
      if not valid: invalid_orders.append((order, "HOLD ERROR: " + msg))

    # Build checks
    for order in build_orders:
      valid, msg = self._build_check(order, power, footer)
      if not valid: invalid_orders.append((order, "BUILD ERROR: " + msg))


    valid_orders = [order for order in orders if order not in [x[0] for x in invalid_orders]]
    for order in valid_orders: self.validate_order(power, order)
    
    if self.game.current_short_phase[0] != "W": # Winter seems to always generate errors?
      if len(self.game.error) > 0:
        print("Uncaught invalid orders")
        print("Thought valid orders: ", valid_orders)
        print("Errors: ", self.game.error)
        raise Exception("Uncaught invalid orders")
    

    if len(invalid_orders) > 0:
      return False, invalid_orders
    else:
      return True, []

    
  def _generic_check(self, order, power, footer):
    parts = order.split(" ")

    # Check that all referenced locations exist
    locs = [part for part in parts if len(part) ==  3]
    bad_locs = [loc for loc in locs if loc not in self.all_locs]
    if bad_locs:
      return order, power + f"Location(s) {', '.join(bad_locs)} do not exist"

    # Check ordered unit actually exists
    if order[:5] not in self.game.get_state()["units"][power]: 
      footer.unit_reminder = True
      if parts[0] == "A":
        return order, f"{power} has no army in {parts[1]}"
      elif parts[0] == "F":
        return order, f"{power} has no fleet in {parts[1]}"
      else:
        return order, f"Unit \"{parts[0]}\" is not a valid unit type"
    
    return True, ""

  def _build_check(self, order, power, footer):
    if self.game.current_short_phase[0] != "W":
      return False, "Can only build in winter phase"
    
    # Do the unit and location exist?
    unit, location, _b = order.split(" ")
    if unit not in ["A", "F"]:
      return False, f"Unrecognised unit type \"{unit}\""
    if location not in self.all_locs:
      return False, f"Location \"{location}\" does not exist"
    
    # Is the location an owned home territory?
    if location not in self.game.map.homes[power]:
      return False, f"Location \"{location}\" is not a home territory for {power}. {power} home territories are {', '.join(self.game.map.homes[power])}"
    if location not in self.game.get_state()["centers"][power]:
      return False, f"Location \"{location}\" is not a controlled by {power}"
    
    # Is the location already occupied by a unit?
    all_units_locs = [x.split(" ")[1] for y in self.game.get_state()["units"].values() for x in y]
    if location in all_units_locs:
      return False, f"Cannot build unit in \"{location}\" as it already has a unit in it"
    
    # Trying to build a fleet in a landlocked territory?
    if location not in self.map.loc_coasts.keys() and unit == "F":
      return False, f"Location \"{location}\" is landlocked, fleets cannot be built here"
    
    return True, ""
    
  def _convoy_check(self, order, power, footer):
    if self.game.current_short_phase[0] not in ["S", "F"]:
      return False, "Cannot convoy in winter"

    # Do locations exist
    if parts[3] not in self.all_locs: 
      return False, f"Location \"{parts[3]}\" does not exist"
    if parts[5] not in self.all_locs:
      return False, f"Location \"{parts[5]}\" does not exist"
    if parts[7] not in self.all_locs:
      return False, f"Location \"{parts[7]}\" does not exist"
    
    parts = order.split(" ")
    if parts[0] != "F":
      return False, "Convoying unit must be a fleet"
    if self.map_loc_type[parts[1]] == "WATER":
      return False, "Convoying unit must be in a sea territory"
    if parts[2] != "C": 
      return False, "Convoy order must contain \"C\" after the unit type and location"
    if parts[4] == "F":
      return False, "Fleets cannot be convoyed"
    if parts[4] != "A":
      return False, f"Unrecognized unit type \"{parts[4]}\""
    if parts[5] not in self.map.loc_coasts.keys():
      return False, f"Location \"{parts[5]}\" is landlocked, and cannot be convoyed from"
    if parts[5] in self.sea_territories:
      return False, f"Location \"{parts[5]}\" is a sea territory, and cannot be convoyed from"
    if parts[6] != "-":
      return False, "Convoy order must contain \"-\" after the conyvoyed units starting location"
    if parts[7] not in self.map.loc_coasts.keys():
      return False, f"Location \"{parts[7]}\" is landlocked, and cannot be convoyed to"
    if parts[7] in self.sea_territories:
      return False, f"Location \"{parts[7]}\" is a sea territory, and cannot be convoyed to"

    # Check that unit being convoyed actually exists
    convoyed_unit = parts[4] + " " + parts[5]
    if convoyed_unit not in self.all_units:
      footer.unit_reminder = True
      return False, f"There is no army in \"{parts[5]}\""
  
  def _support_check(self, order, power, footer):
    if self.game.current_short_phase[0] not in ["S", "F"]:
      return False, "Cannot support in winter"
    parts = order.split(" ")

    if parts[2] != "S":
      return False, "Support order must contain \"S\" after the unit type and location"
    if parts[3] not in ["A", "F"]:
      return False, f"Unit type \"{parts[3]}\" is not a valid unit type"
    if parts[4] not in self.all_locs:
      return False, f"Location \"{parts[4]}\" does not exist"

    # Check that supported unit exists
    supported_unit = parts[3] + " " + parts[4]
    if supported_unit not in self.all_units:
      footer.unit_reminder = True
      return False, f"There is no {parts[3]} in \"{parts[4]}\""
    

    if len(parts) == 5: # Support hold
      if parts[4] not in self.map.dest_with_coasts[parts[1]]:
        return False, f"Supported units location \"{parts[4]}\" is not adjacent to the supporting unit's location, which must be true for a support hold"
    elif len(parts) == 7: # Support move
      if parts[5] != "-":
        return False, "Support order must contain \"-\" after the supported unit location"
      if parts[6] not in self.all_locs:
        return False, f"Location \"{parts[6]}\" does not exist"
      if parts[6] not in self.map.dest_with_coasts[parts[1]]:
        return False, f"Target location \"{parts[6]}\" is not adjacent to the supporting unit's location, which must be true for a support move"
    
    return True, ""

  def _move_check(self, order, power, convoy_orders, invalid_orders,footer):
    if self.game.current_short_phase[0] not in ["S", "F"]:
      return False, "Cannot move in winter"
    parts = order.split(" ")

    if len(parts) != 4:
      return False, "Move order must contain 4 parts"
    if parts[0] not in ["A", "F"]:
      return False, f"Unit type \"{parts[0]}\" is not a valid unit type"
    if parts[1] not in self.all_locs:
      return False, f"Location \"{parts[1]}\" does not exist"
    if parts[2] != "-":
      return False, "Move order must contain \"-\" after the unit location"
    if parts[3] not in self.all_locs:
      return False, f"Location \"{parts[3]}\" does not exist"

    
    # Fleet specific checks
    if parts[0] == "F":
      if self.map_loc_type[parts[3]] == "LAND": # Fleets cannot move to landlocked territories
        return False, f"Fleets cannot move to landlocked territories"
      if parts[3] not in self.map.dest_with_coasts[parts[1]]: # Fleets must always move to adjacent territories
        return False, f"Fleets must move to adjacent territories"
      # Specifically checking for spain coasts, godammit
      if parts[3] == "SPA":
        return False, f"Ambigious order - spain has two coasts. Specify SPA/NC or SPA/SC"

    
    # Army specific checks
    if parts[0] == "A":
      if self.map_loc_type[parts[3]] == "WATER": # Armies cannot move to sea territories
        return False, f"Armies cannot move to sea territories"
      # If checking convoy path, check that the unit has a matching destination convoy order
      if self.check_convoy:
        # Check if territories are adjacent
        if parts[1] not in self.map.dest_with_coasts[parts[3]]:
          matching_convoy_order = False
          error = f"Army cannot move to destination - {parts[1]} is not adjacent to {parts[3]}"
          for order in convoy_orders:
            # Keeping logic for convoying with just one fleet for now
            if order not in [x[0] for x in invalid_orders]: # Convoy order must be valid
              unit_type, fleet_loc, _c, _a, convoy_start, _, convoy_end = order.split(" ")
              if (convoy_start == parts[1]) and (convoy_end == parts[3]):
                # Fleet must be adjacent to both territories
                if (parts[1] in self.map.dest_with_coasts[fleet_loc]) and (parts[3] in self.map.dest_with_coasts[fleet_loc]):
                  matching_convoy_order = True
                  break
          if not matching_convoy_order:
            return False,  error
    

    return True, ""
  
  def _hold_check(self, order, power, footer):
    return True, ""


  def validate_order(self, power, word, expand=True, replace=True):
    """
      Code borrowed from diplomacy package
      Needed slight modification to work here, cannot just call directly
    """
    game = self.game
    word = word.split()


    power = game.powers[power]
    if not word:
      return None

    raw_word = word

    if expand:
      # Check that the order is valid. If not, self.error will say why.
      word = game._expand_order(word)
      word = game._expand_coast(word)
      word = game._add_unit_types(word)
      word = game.map.default_coast(word)

      # Last word is '?' - Removing it
      if word and len(word[-1]) == 1 and not word[-1].isalpha():
        print("1")
        word = word[:-1]
      if len(word) < 2:
        print("2")
        return game.error.append(err.STD_GAME_BAD_ORDER % ' '.join(word))

    # Checking if we can order unit
    unit, order = ' '.join(word[:2]), ' '.join(word[2:])
    owner = game._unit_owner(unit)
    if not owner or owner is not power:
      game.error += [err.STD_GAME_UNORDERABLE_UNIT % ' '.join(word)]
    elif order:
      valid = game._valid_order(power, unit, order)
      return valid