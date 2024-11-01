# From https://github.com/google/vizier/blob/main/README.md
from vizier.service import clients
from vizier.service import pyvizier as vz

import time

start_time = time.time()

# Objective function to maximize.
def evaluate(w: float, x: int, y: float, z: str) -> float:
  if w > 2.5:
    return {'metric': float('-inf')}
  return {'metric': w**2 - y**2 + x * ord(z)}

# Algorithm, search space, and metrics.
study_config = vz.StudyConfig(algorithm='DEFAULT')
# study_config = vz.StudyConfig(algorithm='GP_UCB_PE')
study_config.search_space.root.add_float_param('w', 0.0, 5.0)
study_config.search_space.root.add_int_param('x', -2, 2)
study_config.search_space.root.add_discrete_param('y', [0.3, 7.2])
study_config.search_space.root.add_categorical_param('z', ['a', 'g', 'k'])
study_config.metric_information.append(vz.MetricInformation('metric', goal=vz.ObjectiveMetricGoal.MAXIMIZE))

# Setup client and begin optimization. Vizier Service will be implicitly created.
best_metric = float('-inf') # Initialize to negative infinity to track during study.
study = clients.Study.from_study_config(study_config, owner='my_name', study_id='example')
for i in range(30):
  suggestions = study.suggest(count=25)
  for suggestion in suggestions:
    params = suggestion.parameters
    objective = evaluate(params['w'], params['x'], params['y'], params['z'])

    # Keep track of the best metric and parameters.
    if objective['metric'] > best_metric:
      best_metric = objective['metric']
      best_parameters = params

    suggestion.complete(vz.Measurement(objective))
    print(f'  Suggestion {suggestion.id}: {params} -> {objective}')
  print(f'Completed iteration {i + 1}. Elapsed time: {time.time() - start_time:.2f}s')

print(f'Best parameters: {best_parameters} for metric: {best_metric}')