import ollama
from datetime import datetime
from const import helper

class Chatbot():
    LOG_PATH = "./logs/chatbot.log"
    MODEL = "llama3.2"
    
    def init():
        Chatbot.reset()
        
    def reset():
        helper.chat_log("Reseting history.")
            
        Chatbot.messages = [
            {"role": "system", "content": "You are a chatbot of a discord music bot. Response as if you are a DJ. Make a very short summary message for every song incoming."}
        ]
        
    def chat(prompt, role='user'):
        Chatbot.messages.append({'role': role, 'content': prompt})
        res = ollama.chat(model=Chatbot.MODEL, messages=Chatbot.messages)
        
        assistant_response = res['message']['content']
        print(f"Assistant: {assistant_response}")

        # Add the assistant's response to the history for future turns
        Chatbot.messages.append({'role': 'assistant', 'content': assistant_response})
        
        ## Log 
        helper.chat_log(f"Prompt: {prompt}, Res.: {assistant_response}\n")
            
        return assistant_response
    
    def djUpdate(message):
        return Chatbot.chat("New song incoming, info:" + message, role="user")