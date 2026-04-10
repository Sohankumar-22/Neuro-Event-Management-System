import pickle
import os

model_path = r'c:\Users\kumar\OneDrive\Desktop\Event Planner for review\event_price_model.pkl'
if os.path.exists(model_path):
    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        print(f"Model Type: {type(model)}")
        if hasattr(model, 'n_estimators'):
            print(f"Estimators: {model.n_estimators}")
        if hasattr(model, 'get_params'):
            print(f"Params: {model.get_params()}")
    except Exception as e:
        print(f"Error loading model: {e}")
else:
    print("Model not found")
