from flask import Flask, jsonify, render_template, request
import heapq
import random

app = Flask(__name__)

# Simulation Parameters
params = {
    "lambda": 2.0,  # Arrival rate
    "mu": 20,      # Service rate
    "alpha": 0.001    # Retrial rate (per person in orbit)
}

# Global Simulation State
sim_state = {
    "time": 0.0,
    "server_busy": False,
    "orbit_count": 0,
    "events": [(0.0, "ARRIVAL")], # (time, type)
    "last_event_label": "Start"
}

# Event Types
ARRIVAL = "ARRIVAL"
COMPLETION = "COMPLETION"
RETRY = "RETRY"

def schedule_retrials():
    """Each person in orbit tries to reconnect independently."""
    # In a true retrial queue, retrials are often modeled as a Poisson process
    # with rate = orbit_count * alpha
    if sim_state["orbit_count"] > 0:
        retrial_time = sim_state["time"] + random.expovariate(sim_state["orbit_count"] * params["alpha"])
        heapq.heappush(sim_state["events"], (retrial_time, RETRY))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def get_data():
    # Process events until we move forward in time or reach a significant state change
    if not sim_state["events"]:
        return jsonify(sim_state)

    # Pop the next event
    event_time, event_type = heapq.heappop(sim_state["events"])
    sim_state["time"] = event_time
    sim_state["last_event_label"] = event_type

    if event_type == ARRIVAL:
        if not sim_state["server_busy"]:
            sim_state["server_busy"] = True
            finish_time = sim_state["time"] + random.expovariate(params["mu"])
            heapq.heappush(sim_state["events"], (finish_time, COMPLETION))
        else:
            sim_state["orbit_count"] += 1
            schedule_retrials()
        
        # Schedule next arrival
        next_arrival = sim_state["time"] + random.expovariate(params["lambda"])
        heapq.heappush(sim_state["events"], (next_arrival, ARRIVAL))

    elif event_type == COMPLETION:
        sim_state["server_busy"] = False
        # After completion, check if anyone in orbit wants to try
        schedule_retrials()

    elif event_type == RETRY:
        # If server is free, the retrial succeeds
        if not sim_state["server_busy"] and sim_state["orbit_count"] > 0:
            sim_state["orbit_count"] -= 1
            sim_state["server_busy"] = True
            finish_time = sim_state["time"] + random.expovariate(params["mu"])
            heapq.heappush(sim_state["events"], (finish_time, COMPLETION))
        else:
            # If server was busy, they stay in orbit and will try again later
            schedule_retrials()

    return jsonify({
        "orbit_count": sim_state["orbit_count"],
        "server_busy": sim_state["server_busy"],
        "time": round(sim_state["time"], 2),
        "event": sim_state["last_event_label"]
    })

@app.route('/settings', methods=['POST'])
def update_settings():
    new_settings = request.json
    params.update(new_settings)
    return jsonify({"status": "updated", "params": params})

if __name__ == '__main__':
    # Using 5001 to avoid the MacOS AirPlay conflict
    app.run(debug=True, port=5001)
