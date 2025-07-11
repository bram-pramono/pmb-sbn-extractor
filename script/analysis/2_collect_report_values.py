import os
import csv

sub_folder = 'tmp'

base_folder = '/home/pramono/work/drs/pmb-sbn-extractor/report/r-analysis/'
report_folder = base_folder + sub_folder
# walk through all files

report_data = []
for root, dirs, files in os.walk(report_folder):
  for f in files:
    filepath = f'{root}/{f}'
    f_name_parts = f.split('_')
    a_type = f_name_parts[0]
    d_type = f_name_parts[1]

    with open(filepath, 'r') as raw_file:
      lines = raw_file.readlines()
      formula = lines[1]
      form_parts = formula.split('~')
      indep_var = form_parts[0][9:].strip()
      dep_var = form_parts[1].split('*')[0].strip()
      for line in lines:
        line = line.replace('< 2e-16', '<2e-16')
        if line.startswith(dep_var) and ':' not in line:
          items = [x for x in line.split(' ') if len(x) > 0]
          est = items[1]
          t_val = items[4]
          p_val = items[5]
          sig = items[6].replace('\n', '') if len(items) > 6 else ''
          cross_intercept = f_name_parts[-1].replace('.txt', '')
          report_data.append((d_type, a_type, indep_var, dep_var, est, t_val, p_val, sig, cross_intercept, f))
          break

with open(f'{base_folder}summary_{sub_folder}.tsv', 'w') as out:
  cwriter = csv.writer(out, delimiter='\t')
  cwriter.writerow(('data_type', 'focus_topic', 'indep_var', 'dep_var', 'est', 't_val', 'p_val', 'sig', 'x_intercept', 'file'))

  for x in report_data:
    cwriter.writerow(x)
