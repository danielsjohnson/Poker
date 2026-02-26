# calling_station.py

def calling_station_action(valid_actions):
    """
    Returns the action index for a Calling Station (Always Call/Check).
    
    Action Mapping:
    0: Fold
    1: Check (if to_call=0) / Fold (if to_call>0)
    2: Call
    3-5: Raise
    6: All-In
    """
    

    if valid_actions[1] == 1:
        return 1
        

    if valid_actions[2] == 1:
        return 2
        

    if valid_actions[6] == 1:
        return 6
        
    return 1