# From https://github.com/google/vizier/blob/main/README.md
from vizier.service import clients
from vizier.service import pyvizier as vz
from interface import iterate, evaluate

import time
import random
random.seed(9101) # Seed 9101 Count(Batch) = 25


start_time = time.time()

# Algorithm, search space, and metrics.
study_config = vz.StudyConfig(algorithm='DEFAULT')
study_config.search_space.root.add_float_param('Wx_inpmos_1', 0.25, 10)
study_config.search_space.root.add_float_param('Lx_1', 0.13, 10)
study_config.search_space.root.add_float_param('Lx_2', 0.13, 10)
study_config.search_space.root.add_float_param('Wx_innmos_1', 0.25, 10)
study_config.metric_information.append(vz.MetricInformation('metric', goal=vz.ObjectiveMetricGoal.MINIMIZE))

# Setup client and begin optimization. Vizier Service will be implicitly created.
best_metric = float('inf') # Initialize to infinity to track metrics during "MINIMIZE" study.
objective = {} # Initialize to empty dictionary to store the objective metric.
study = clients.Study.from_study_config(study_config, owner='cyl', study_id='inverter_sizing_test')
for i in range(10):
  # Generate suggestions
  suggestions = study.suggest(count=25)
  
  # Print the values of the suggestions
  for suggestion in suggestions:
    print(f'Suggestion {suggestion.id}: {suggestion.parameters}')
  
  # Setup and run simulations via ngspice
  results = iterate(suggestions)
  # Evaluate results to get metrics
  metrics = evaluate(results)

  # Iterate through suggestions and metrics to complete them.
  inout = zip(suggestions, metrics)
  for suggestion, metric in inout:
    params = suggestion.parameters
    objective['metric'] = metric

    # Keep track of the best metric and parameters.
    # Modify comparison based on minimum or maximum goal.
    if objective['metric'] < best_metric:
      best_metric = objective['metric']
      best_parameters = params

    suggestion.complete(vz.Measurement(objective))
    print(f'  Suggestion {suggestion.id}: {params} -> {objective}')
  print(f'Completed iteration {i + 1}. Elapsed time: {time.time() - start_time:.2f}s')

print(f'Best parameters: {best_parameters} for metric: {best_metric}')