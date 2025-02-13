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
from tools.modelchat import ModelChat, ChatComponent
from tools.modelwrapper import DiploModel

#####

LLM_MODEL = "gemini-2.0-flash-thinking-exp"
API_WAIT_SECS = 6

#####

with open(Path("C:/Users/ray/Documents/api_keys/gemini.txt")) as file:
  gemini_api_key = file.read()

genai.configure(api_key=gemini_api_key)

config = genai.GenerationConfig(
  stop_sequences=["END THOUGHTS", "END ORDERS"]
)

#####

game = Game()
parser = StateParser()
move_checker = MoveChecker(game, parser)
prompt_handler = PromptHandler(game, parser, "FRANCE")
chat = ModelChat()

model = DiploModel(LLM_MODEL)
model.add_config("BASIC", genai.GenerationConfig(stop_sequences=["END THOUGHTS", "END ORDERS"]))

# Should be set to one of: ["UNDEFINED", "PROMPT", "THOUGHT", "ORDER", "ERROR"]
while True:
  possible_orders = game.get_all_possible_orders()

  for power_name, power in game.powers.items():
    if power_name == "FRANCE":
      if game.current_short_phase == "S1901M": prompt = prompt_handler.opening_prompt
      else                                   : prompt = prompt_handler.thought_prompt

      print(prompt)
      chat.add_message("PROMPT", prompt)
      sleep(API_WAIT_SECS)
      response = model.generate_content(chat.chat, "BASIC")
      print(response.text)
      chat.add_message("THOUGHT", response.text)

      chat.add_message("PROMPT", prompt_handler.order_prompt)
      print(prompt_handler.order_prompt)

      sleep(API_WAIT_SECS)
      response = model.generate_content(chat.chat, "BASIC")
      response_text = response.text
      chat.add_message("ORDER", response_text)
      print(response_text)

      if response_text.split("\n")[0] == "WAIVE": 
        response_text = ""

      for i in range(5):
        order_error, error_string = move_checker.check_all_orders(power_name, response_text)

        if order_error:
          prompt = prompt_handler.get_error_prompt(error_string)
          chat.add_message("ERROR", prompt)
          print(error_string)

          sleep(API_WAIT_SECS)
          response = model.generate_content(prompt, "BASIC")
          chat.add_message("THOUGHT", response.text)
          print(response.text)
          

          chat.add_message("PROMPT", chat.chat)
          print(prompt_handler.order_prompt)

          sleep(API_WAIT_SECS)
          response = model.generate_content(chat.chat, "BASIC")
          response_text = response.text

          chat.add_message("ORDER", response_text)
          print(response_text)

          game.error = []
          
        else:
            break
      
      power_orders = response_text.split("\n")
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

try: os.remove('saved_games/game_gemini.json')
except FileNotFoundError: pass
to_saved_game_format(game, output_path='saved_games/game_gemini.json')

#####


