import ollama
from datetime import datetime
from const import helper
import time
import asyncio
import ServersHub

class Chatbot():
    CLIENT = ollama.Client(timeout=40)
    LOG_PATH = "./logs/chatbot.log"
    MODEL = "gemma3"
    class Queue():
        def __init__(self):
            self.q: list = []
        
        def add(self, i):
            self.q.append(i)
        def pop(self):
            if len(self.q) > 0:
                return self.q.pop(0)
            return None
    queue = Queue()
    
    def parserLoop():
        while True:
            item = Chatbot.queue.pop()
            if (item == None): 
                time.sleep(1)
                continue;
            
            ##### START #####
            # deconstruct
            prompt, role, func = item
            print("Handing prompt:", prompt) 
            
            Chatbot.lastReply = ""
            Chatbot.messages.append({'role': role, 'content': prompt})
            assistant_response = ""
            try: 
                stream = Chatbot.CLIENT.chat(model=Chatbot.MODEL, messages=Chatbot.messages)

                for chunk in stream:
                    # print(chunk)
                    if 'message' not in chunk: 
                        print(chunk, "skip")
                        continue
                    print(chunk[1])
                    content = chunk[1].content
                    assistant_response += content
                    print(content, end='', flush=True) # Print partial results

            except Exception as e:
                print(f"\nRequest timed out or failed: {e}")
                print(f"--- Partial Result ({len(assistant_response)} chars) ---")


            print(f"Assistant: {assistant_response}")
            # Add the assistant's response to the history for future turns
            Chatbot.messages.append({'role': 'assistant', 'content': assistant_response})
            Chatbot.lastReply = assistant_response
            ## Log 
            helper.chat_log(f"Prompt: {prompt}, Res.: {assistant_response}\n")
            try:
                func(assistant_response)
            except Exception as e:
                helper.error_log(f"Cannot run func given by prompt: {prompt}\nRes: {assistant_response}")
                helper.error_log_e(e)
                pass
            ##### END #####
            
            ## SLEEP 
            time.sleep(1)
    
    def init():
        Chatbot.reset()
        
    def reset():
        helper.chat_log("Reseting history.")
            
        Chatbot.messages = [
            {"role": "system", "content": "You are a chatbot of a discord music bot. Response as if you are a DJ. The system will give you update for every new song incoming, make short message for the audience."}
        ]
        Chatbot.lastReply = ""
        
    def chat(prompt, role='user', func=lambda res: {}):
        Chatbot.queue.add((prompt, role, func))
    
    def djUpdate(message, func=lambda res: {}):
        return Chatbot.chat("New song incoming, info:" + message, role="system", func=func)