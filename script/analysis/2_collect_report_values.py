import csv
import os

from script.sbnutils import result_folder
from script.utils import to_abspath

show_all_coef = False
sub_folder = '20250711'

r_analysis_result_folder = to_abspath(result_folder, 'r-analysis', sub_folder)

report_data = []
for root, dirs, files in os.walk(r_analysis_result_folder):
  for f in files:
    filepath = f'{root}/{f}'
    f_name_parts = f.split('_')
    s_type = f_name_parts[0]
    a_type = f_name_parts[1]
    d_type = f_name_parts[2]

    with open(filepath, 'r') as raw_file:
      raw_file_content = raw_file.read()
      raw_lines = raw_file_content.split('\n')
      formula = raw_lines[1]
      form_parts = formula.split('~')
      dep_var = form_parts[0][9:].strip()
      indep_var = form_parts[1].split('*')[0].strip()

      file_content_parts = raw_file_content.split('Fixed effects:')
      result_content = file_content_parts[1].split('---')[0]
      lines = result_content.split('\n')
      for line in lines[2:-1]:
        line = line.replace('< 2e-16', '<2e-16')
        if show_all_coef or (line.startswith(indep_var) and ':' not in line):
          items = [x for x in line.split(' ') if len(x) > 0]
          coef = items[0]
          est = items[1]
          t_val = items[4]
          p_val = items[5]
          sig = items[6].replace('\n', '') if len(items) > 6 else ''
          cross_intercept = f_name_parts[-1].replace('.txt', '')
          report_data.append((s_type, d_type, a_type, dep_var, indep_var, coef, est, t_val, p_val, sig, cross_intercept, f))

with open(to_abspath(result_folder, f'summary_{sub_folder}.tsv'), 'w') as out:
  cwriter = csv.writer(out, delimiter='\t')
  cwriter.writerow(('source', 'data_type', 'focus_topic', 'dep_var', 'indep_var', 'coef', 'est', 't_val', 'p_val', 'sig', 'x_intercept', 'file'))

  for x in report_data:
    cwriter.writerow(x)
