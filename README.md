To develop inside osic container in vs code, install docker dev containers extension and use the “attach to container” function after starting the container with shell script.

Once inside the container, clone the repo and start the virtual environment and install requirements from requirements.txt using python -m pip install -r requirements.txt.

From Vizier_Circuit_Solver directory run:
Vizier_Circuit_Solver > python OpAmp_Optimization/interface.py to setup parameter files and get modified code for new study parameters.

Modify sizing test with code from interface.py output before running sizing routine.
Vizier_Circuit_Solver > python OpAmp_Optimization/inverter_sizing_test.py