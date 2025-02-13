class ChatComponent():
  # Should be set to one of: ["UNDEFINED", "PROMPT", "THOUGHT", "ORDER", "ERROR"]
  type = "UNDEFINED"
  content = ""

  def __init__(self, type=None, content=None):
    if type: self.type = type
    if content: self.content = content

  def __repr__(self):
    return self.content

  def __str__(self):
    return self.content

  def __add__(self, other):
    print(other, type(other))
    print(self, type(self))

    return other + self.content

  

class ModelChat:
  def __init__(self):

    self.model_thoughts = []
    self.model_orders = []
    self.system_responses = []
    self.system_error = []

    self.type_map = {
      "THOUGHT" : self.model_thoughts,
      "ORDER" : self.model_orders,
      "PROMPT" : self.system_responses,
      "ERROR" : self.system_error
    }

    self.chat_history = []


  def add_message(self, type: str, content:str) -> None:
    if type not in self.type_map.keys():
      raise ValueError(f"Type {type} not in regnoised types [{', '.join(list(self.type_map.keys()))}]")
    
    message = ChatComponent(type, content)
    self.type_map[type].append(message)
    self.chat_history.append(message)
  

  def remove_last_message(self) -> None:
    type = self.chat_history[-1]

    self.type_map[type].pop(-1)
    self.chat_history.pop(-1)
  

  def construct_chat(self) -> str:
    return "\n".join([c.content for c in self.chat_history])
  
  @property
  def chat(self):
    return self.construct_chat()

  def __str__(self) -> str:
    return self.construct_chat()