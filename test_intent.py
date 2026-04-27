from world.intent_manager import IntentManager
im = IntentManager()
intent, confidence, slots = im.classify("look merchant")
print(f"Intent: {intent}, Confidence: {confidence}, Slots: {slots}")