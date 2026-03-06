class StatePacketViewer:
    def __init__(self, state_packet):
        self.state_packet = state_packet

    def display(self):
        import streamlit as st
        st.subheader("Current State Packet (ACT)")
        st.json(self.state_packet.get_current_state())
