# Python file version of ai_testing.ipynb
# For each of reading on github

import json
import random
import os
import string

from pathlib import Path
from time import sleep

import google.generativeai as genai

from diplomacy import Game
from diplomacy.utils.export import to_saved_game_format
import diplomacy.utils.errors as err

from tools.movechecker import MoveChecker
from tools.stateparser import StateParser

#####

with open(Path("C:/Users/ray/Documents/api_keys/gemini.txt")) as file:
  gemini_api_key = file.read()

genai.configure(api_key=gemini_api_key)

config = genai.GenerationConfig(
  stop_sequences=["END THOUGHTS", "END ORDERS"]
)

#####

with open(Path("./prompts/opening_prompt.txt")) as file:
  opening_prompt = file.read()

#####

game = Game()
parser = StateParser()
move_checker = MoveChecker(game, parser)

reminder_phrase = "You should now write a few sentences detailing the current state of the game, and your plans for your next order. Keep this brief, and do not include any orders in standard diplomacy notation.\n"
reminder_phrase += "Reminder: You must end your response with 'END THOUGHTS', and only submit orders after you receive a SUBMIT ORDERS command.\n"

mistake_reminder = "You should now write a sentence on what went wrong, and how you will fix it. Keep this brief, and do not include any orders in standard diplomacy notation.\n"

order_reminder = "Remember: After SUBMIT ORDERS, you must only repond with your orders in standard diplomacy notation, seperated by newlines, then with phrase \"END ORDERS\"\n"

model = genai.GenerativeModel('gemini-2.0-flash-thinking-exp', generation_config=config)
chat = model.start_chat(history=[]) 

response = chat.send_message(opening_prompt)

for i in range(15):
  possible_orders = game.get_all_possible_orders()

  # For each power, randomly sampling a valid order
  for power_name, power in game.powers.items():
    current_phase = game.get_current_phase()
    if power_name == "FRANCE":
      if current_phase == "S1901M":
        current_state = "GAME START\n\nBEGIN THOUGHTS"
      else:
        current_state = json.dumps(game.get_state())
        current_state = parser.parse_state(game)
        phase_intro = parser.get_phase_intro(game)
        current_state = "END ORDERS\n\n" + current_state + "\n" + phase_intro + "\n" + reminder_phrase + "\n" + "BEGIN THOUGHTS" + "\n"

      print(current_state)
      sleep(4)
      response = chat.send_message(current_state)
      print(response.text)

      sleep(4)
      response = chat.send_message(f"END THOUGHTS\n\n{order_reminder}\n\nSUBMIT ORDERS\n")
      response_text = response.text
      if response_text.split("\n")[0] == "WAIVE": response_text = ""

      for i in range(5):
        print(response_text)
        order_error, error_string = move_checker.check_all_orders(power_name, response_text)

        if order_error:
          print(error_string)
          sleep(4)
          response = chat.send_message(error_string)
          print(response.text)

          sleep(4)
          response = chat.send_message(f"END THOUGHTS\n\n{order_reminder}\n\nSUBMIT ORDERS\n")
          response_text = response.text
          game.error = []
          
        else:
            break

      game.set_orders("FRANCE", response_text.split("\n"))
    else:
      power_orders = [random.choice(possible_orders[loc]) for loc in game.get_orderable_locations(power_name)
                      if possible_orders[loc]]


    game.set_orders(power_name, power_orders)

  game.process()
  if game.is_game_done:
    break

#####

# Show entire chat history
print("\n".join([x.parts[0].text for x in chat.history]))

#####

os.remove('saved_games/game_gemini.json') # File corrupts if not removed first
to_saved_game_format(game, output_path='saved_games/game_gemini.json')

#####


