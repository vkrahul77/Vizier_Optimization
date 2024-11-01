import re
import json

import numpy as np

import os # Used to call ngspice

import pandas as pd # Used to extract csv results

'''
Take a base template file and enumerate all variables with its base name and an id
'''
def enumerate_variables(template_file, output_file):
    with open(template_file, 'r') as f:
        template = f.read()

    # For each instance of a variable, enumerate it
    # - Variable format is specified as *$variable_name\s*
    # - Track the enumerations of different variables separately
    # - Replace the variable with the enumeration
    variables = {}

    def replace_match(match):
        variable = match.group(1)
        # Special case when the variable is $index (ignore)
        if variable == 'index':
            return match.group(0)
        # Otherwise record the variable and enumerate it
        if variable not in variables:
            variables[variable] = 0
        variables[variable] += 1
        return '$%s_%d ' % (variable, variables[variable])

    # Use re.sub with a callback function to replace each match individually
    template = re.sub(r'\$\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*', replace_match, template)

    # print(variables)

    # Store variables to a json file
    with open(f'{output_file}.json', 'w') as f:
        json.dump(variables, f)

    # Write the output to a file
    with open(f'{output_file}.txt', 'w') as f:
        f.write(template)
        

'''
Generate a batched set of randomized parameters from the enumerated json file.
This function is meant to handle transistor widths and lengths.
Within the function, width and length parameters are known based on the first letter of the variable name.
For widths and lengths, the range of values can be set independently.
Returns a set of parameters in dictionary format.
'''
def generate_parameters(json_file, batch_size, W_range=(0.25, 10), L_range=(0.13, 10), truncation=2):
    np.random.seed(1337)

    with open(json_file, 'r') as f:
        variables = json.load(f)
        
    parameters = []
    for i in range(batch_size):
        parameter = {}
        for variable, count in variables.items():
            for i in range(count):
                if variable[0] == 'W':
                    # Sample uniformly from the range and truncate to {truncation} decimal places
                    parameter[variable+f'_{i+1}'] = round(np.random.uniform(W_range[0], W_range[1]), truncation)
                elif variable[0] == 'L':
                    parameter[variable+f'_{i+1}'] = round(np.random.uniform(L_range[0], L_range[1]), truncation)
                else:
                    raise ValueError('Unknown variable type')
                
        parameters.append(parameter)

    # Write to json with batch index as the first level
    zipped_parameters = list(zip(range(batch_size), parameters))
    with open(f'{json_file[:-5]}_batched_parameters.json', 'w') as f:
        json.dump(zipped_parameters, f, indent=4)

    return parameters

'''
Using the enumerated template and the batched parameters, generate a single netlist with an instantiation for each parameter set.
'''
def generate_netlist(template_file, json_parameter_file, output_file):
    #############################################
    ## FIXME: Hard coded netlist files for now ##
    #############################################
    with open('OpAmp_Optimization/templates/instance_components.template', 'r') as f:
        instance_components = f.read()
    with open('OpAmp_Optimization/templates/TESTBENCH_TOP.template', 'r') as f:
        testbench_top = f.read()
    with open('OpAmp_Optimization/templates/TESTBENCH_TOP.json', 'r') as f:
        testbench_top_parameters = json.load(f)
    # Replacement of testbench parameters
    [testbench_top := testbench_top.replace(f'${key}', str(value)) for key, value in testbench_top_parameters['parameters'].items()]


    with open(template_file, 'r') as f:
        template = f.read()

    with open(json_parameter_file, 'r') as f:
        parameters = json.load(f)

    # A string generator for each instance separation for spice file readability
    def separator(index):
        sep = '\n\n'
        for i in range(2):
            sep += '*************************************************************\n'
        sep += f'********************End Index {index}******************************\n'
        for i in range(2):
            sep += '*************************************************************\n'
        return sep+'\n'

    # For each parameter set, instantiate a new block
    netlist = ''
    for i, parameter in parameters:
        temp = instance_components + '\n\n' + template
        temp = temp.replace('$index', str(i+1))
        [temp := temp.replace(f'${key}', str(value)) for key, value in parameter.items()]
        netlist += temp + separator(i)

    netlist += testbench_top

    with open(output_file, 'w') as f:
        f.write(netlist)

#####################################################
# Under construction - hard coded for op simulation #
#####################################################
def extract_csv_result(file, batch_size):
    # Create pandas object from input file
    df = pd.read_csv(file, sep='\s+')
    repeated_columns = set()
    # Use regex to extract repeated columns which have a name in the format '*.#' (dot number)
    for col in df.columns:
        match = re.match(r'([\w#]+)\.(\d+)', col)
        if match:
            repeated_columns.add(col)

    # Remove repeated columns from the df
    df = df.drop(columns=repeated_columns)

    results = {}
    for i in range(batch_size):
        results[i+1] = {}
        results[i+1]['vout'] = df[f'out_{i+1}'][0]
        results[i+1]['id'] = df[f'vsource_{i+1}#branch'][0] * -1

    return results

def write_search_space_code(ifile, W_range=(0.25, 10), L_range=(0.13, 10)):
    '''
    Reads a json file and writes code to add parameters to the search space.
    For now, only supports Width and Length parameters.
    Expects variable names to start with 'W' or 'L'.
    '''
    # Load json file
    with open(ifile, 'r') as f:
        search_space = json.load(f)
    
    # Search space contains the base name of the variable and the number of instances
    # - Example: {"Wx_inpmos": 1, "Lx": 2, "Wx_innmos": 1}
    for variable, count in search_space.items():
        if variable[0] == 'W':
            for i in range(count):
                print(f"study_config.search_space.root.add_float_param('{variable}_{i+1}', {W_range[0]}, {W_range[1]})")
        elif variable[0] == 'L':
            for i in range(count):
                print(f"study_config.search_space.root.add_float_param('{variable}_{i+1}', {L_range[0]}, {L_range[1]})")
        else:
            raise ValueError('Unknown variable type')

def convert_suggestions_to_batched_parameters(suggestions, json_file, truncation=2):
    '''
    Convert a list of suggestions to a batched parameter format
    '''
    batch_size = len(suggestions)

    # Directly modify all suggestions.suggestion.parameter floating point values to truncated values
    for suggestion in suggestions:
        for key, value in suggestion.parameters.items():
            suggestion.parameters[key] = round(value, truncation)

    parameters = []
    for suggestion in suggestions:
        parameter = suggestion.parameters
                
        parameters.append(parameter)

    # Write to json with batch index as the first level
    zipped_parameters = list(zip(range(batch_size), parameters))
    with open(f'{json_file[:-5]}_batched_parameters.json', 'w') as f:
        json.dump(zipped_parameters, f, indent=4)

    return parameters

def iterate(suggestions):
    '''
    Takes the suggestions and performs the following steps:
    - Convert the suggestions to batched parameters
    - Generate a netlist
    - Run ngspice
    - Extract results
    - Return results
    '''
    batch_size = len(suggestions)

    json_file = 'OpAmp_Optimization/autogen/scratch.json'
    batched_json_file = 'OpAmp_Optimization/autogen/scratch_batched_parameters.json'
    netlist_file = 'OpAmp_Optimization/autogen/scratch.netlist'
    output_file = 'OpAmp_Optimization/simulations/output.txt'

    convert_suggestions_to_batched_parameters(suggestions, json_file)
    generate_netlist('OpAmp_Optimization/autogen/scratch.txt', batched_json_file, netlist_file)
    os.system(f'ngspice -b {netlist_file}')
    results = extract_csv_result(output_file, batch_size)

    return results

def evaluate(results):
    '''
    Takes a group of results and returns the metric.
    Evaluation function in charge of scoring the result.
    '''
    metric = []
    for i in range(len(results)):
        # Look at vout, is this within +/- 10% of 0.6V?
        # Graduated penalty for being further away
        vout = results[i+1]['vout']
        id = results[i+1]['id']
        if vout < 0.2 or vout > 1.0:
            metric.append(float(1e9))
        elif vout < 0.4 or vout > 0.8:
            metric.append(float(1e6))
        elif vout < 0.54 or vout > 0.66:
            metric.append(float(1e3))
        else:
            metric.append(id)

    return metric
    
if __name__ == '__main__':
    '''
    Script can be run to setup parameter sweep and study setup
    '''
    enumerate_variables('OpAmp_Optimization/templates/inverter.template', 'OpAmp_Optimization/autogen/scratch')
    print("\n\n")
    print("Copy this code to your script:")
    write_search_space_code('OpAmp_Optimization/autogen/scratch.json')
    print("\n\n")