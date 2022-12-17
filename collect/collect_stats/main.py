import requests
import json
from db import Base, get_db
from models import GameStratzSchema
from datetime import datetime
from secret import api_token

url = "https://api.stratz.com/graphql"
headers = {"Authorization": f"Bearer {api_token}"}
re = ''

# https://discord.com/channels/268890221943324677/647656115588300800/1039239819596931204

def send_request():
  query = """
    query
    {
      live
      {
        match(id:""" + str(id) +""")
        {
          direScore
          radiantScore
          gameMinute
        }
      }
    }
  """
  re = requests.post(url, json={"query":query}, headers=headers)
  print (re.text)
  return re.text
  
def read_response(raw):
  data = {}
  jas = json.loads(raw)
  baked = jas['data']['live']['match']
  data['direScore'] = baked['direScore']
  data['radiantScore'] = baked['radiantScore']
  data['gameMinute'] = baked['gameMinute']
  return data

def write_stat(data):
  with get_db() as session:
    new_stat = GameStratzSchema(
      radiant_score=data['direScore'], dire_score=data['radiantScore'], gameMinute=data['gameMinute'], timestamp=datetime.now()
    )
  session.add(new_stat)
  session.commit()
  
if __name__ == "__main__":
  id = input('Enter game id: ')
  print(id)
  Base.metadata.create_all()
  for x in range(500):
    raw = send_request()
    print(f'compiled data:')
    data = read_response(raw)
    print(data)
    write_stat(data)
