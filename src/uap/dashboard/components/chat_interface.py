class ChatInterface:
    def __init__(self):
        self.messages = []

    def display_chat(self):
        import streamlit as st
        for msg in self.messages:
            st.chat_message(msg['role']).markdown(msg['content'])

    def capture_input(self):
        import streamlit as st
        user_input = st.chat_input("Type your message here...")
        if user_input:
            self.messages.append({"role": "user", "content": user_input})
            self.process_input(user_input)

    def process_input(self, user_input):
        response = f"Echo: {user_input}"
        self.messages.append({"role": "assistant", "content": response})
