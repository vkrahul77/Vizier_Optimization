import json

# Load json file
ifile = "OpAmp_Optimization/pmos_diff_pair.json"
with open(ifile, 'r') as f:
    search_space = json.load(f)

keyword = {"search"}

# Descend search space until the keyword is found
# Return the dictionary at the keyword level along with the path
# Do this recursively for all nested dictionaries
def descend_search_space(search_space, keyword, name='', paths = [], parameters=[]):
    for key, value in search_space.items():
        if key in keyword:
            parameters.append(value)
            paths.append(name)
        else:
            descend_search_space(value, keyword, name + '.' + key, paths, parameters)
    return zip(paths,parameters)

p = descend_search_space(search_space, keyword)

for i in p:
    # Check if i[1] has 'from' and 'to' keys
    if 'from' in i[1] and 'to' in i[1]:
        print(f"study_config.search_space.root.add_float_param({i[0]}, {i[1]['from']}, {i[1]['to']})")
    else:
        print("No 'from' and 'to' keys found in the dictionary")


