from time import sleep

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

class DiploModel():

  def __init__(self, model_type, configs=dict(), exhaust_wait=30):
    self.model_type = model_type
    self.configs = configs
    self.exhaust_wait = exhaust_wait


  def add_config(self, name, config):
    self.configs[name] = config
  
  
  def generate_content(self, prompt, config_key=None):
    model = genai.GenerativeModel(self.model_type)
    for i in range(10):
      try:
        if config_key: return model.generate_content(str(prompt), generation_config=self.configs[config_key])
        else         : return model.generate_content(str(prompt))
      except ResourceExhausted:
        print("-------429 RESOURCE EXHAUSTED-----------")
        sleep(self.exhaust_wait)
