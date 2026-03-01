from os import mkdir
from os.path import exists, dirname, join
from textx import metamodel_from_file
import jinja2
import argparse

import subprocess

current_folder = dirname(__file__)
mmodel_folder = join(current_folder, 'dsl/')
model_folder = join(current_folder, 'models/')
template_folder = join(current_folder, 'dsl/')
domain_folder = join(current_folder, 'domains/')
output_folder = join(current_folder, '')

def run(args):
      
    mm = metamodel_from_file(mmodel_folder + 'dsl_grammar.tx')
    model = mm.model_from_file(model_folder + args.model)

    print("Tree:",model.tree.levels)
    print("Modeling purpose:", model.problem.purpose)
    ordered_tasks = sorted(model.tasks, key=lambda x: x.level)
    for t in ordered_tasks:
        print(f"Level: {t.level} Task: {t.name}")
        print("#Assessments:", len(t.assessments))
    if model.notation is None:
        print("Model Notation not specified. Step not executed." )
    else:
        print("Model Notation:", model.notation.name)

    domain_description = None
    if args.domain:
        with open(domain_folder + args.domain, 'r') as f:
            domain_description = f.read()
    else:
        domain_description = model.problem.domain
    print("Domain:", domain_description)

    #if not exists(output_folder):
    #    mkdir(output_folder)
    
    log_name = args.model.replace(".dmtot", "")
    if args.domain:
        log_name += f'_{args.domain.replace(".txt", "")}'
    log_name +=  ".log"

    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_folder),
        trim_blocks=True,
        lstrip_blocks=True)

    template = jinja_env.get_template('py_template.template')

    with open(join(output_folder, "%s.py" % "main"), 'w') as f:
        f.write(template.render(problem=model.problem, domain = domain_description, tasks=model.tasks, tree=model.tree, notation=model.notation, model=args.model, output=log_name))

    subprocess.run(["python", "main.py"]) 


def parse_args():
    args = argparse.ArgumentParser()
    args.add_argument('--model', type=str, required=True, help="Domain model decomposition for ToT", default='domain_model.dmtot')
    args.add_argument('--domain', type=str, required=False, help="Optional domain parameter", default=None)
    args = args.parse_args()
    return args
    

if __name__ == '__main__':
    args = parse_args()
    print(args)
    run(args)