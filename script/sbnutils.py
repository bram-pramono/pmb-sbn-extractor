import ast
import copy
import csv
import re
from collections import defaultdict

from easydict import EasyDict

from script.utils import to_abspath


def parse_research_data(folder):
  with open(to_abspath(folder, 'stimuli.txt')) as raw_file:
    csv_reader = csv.DictReader(raw_file, delimiter='\t')
    stimuli_ref = {row['sentence']: row for row in csv_reader}

  return stimuli_ref


SEPARATORS = ['NEGATION', 'CONJUNCTION', 'CONTINUATION', 'RESULT', 'ELABORATION', 'EXPLANATION', 'PRECONDITION', 'POSSIBILITY', 'CONTRAST',
              'CONSEQUENCE', 'ATTRIBUTION', 'NECESSITY']

EVENT_PREDICATES = ['Theme', 'Agent', 'Destination', 'Location', 'Recipient', 'Topic', 'Source', 'Patient', 'Causer', 'Stimulus',
                    'Experiencer', 'Pivot', 'Path', 'Beneficiary', 'Attribute', 'Goal', 'Co-Theme', 'Duration', 'Result', 'Instrument', 'Participant',
                    'Product', 'Value', 'Asset']

RESOLUTION_SYMBOLS = ['≻', '≺', '≠', '⋈', '=', '≈', '⊏', '>', '≤']

MODAL_WORDS = ['want', 'need', 'know', 'refuse', 'continue', 'think', 'wish', 'hope', 'keep']

CONTINUATION_WORDS = ['and', 'when', 'while', 'before', 'if', 'but', 'then', 'whenever']

base_folder = '/home/pramono/work/drs/local_neural_drs'
stimuli_folder = to_abspath(base_folder, 'thesis/data/frank_etal/')

sent_nr_ref = {value['sent_nr']: value for value in parse_research_data(stimuli_folder).values()}


def parse_sbn_distance(ana_distance: str):
  if ana_distance.startswith('+'):
    return int(ana_distance[1:])
  elif ana_distance.startswith('-'):
    return int(ana_distance[1:]) * -1
  else:
    return 0


def extract_sent_token_spans(text):
  spans = []
  last_idx = 0
  for m in re.finditer(' ', text):
    spans.append((last_idx, m.start()))
    last_idx = m.end()
  spans.append((last_idx, len(text)))
  return spans


def find_in_array(array, start: int, end: int):
  token_idxs = []
  copy_array = list(array)
  while len(copy_array) > 0:
    last_span = copy_array.pop(0)
    if last_span[0] == start:
      token_idxs.append(len(array) - len(copy_array) - 1)
      # when both start and end has a match
      if last_span[1] >= end:
        return token_idxs
      else:
        # keep collecting until end has matched
        while len(copy_array) > 0:
          last_span = copy_array.pop(0)
          token_idxs.append(len(array) - len(copy_array) - 1)
          if last_span[1] >= end:
            return token_idxs
    # merge this token with the previous
    elif last_span[1] == end:
      token_idxs.append(len(array) - len(copy_array) - 1)
      return token_idxs

  return token_idxs


def determine_ori_sent_token_idxs_based_on_sbn(sent_nr, start_idx, end_idx):
  global sent_nr_ref
  sent = sent_nr_ref[sent_nr]['sentence']
  tokens = sent.split(' ')
  token_spans = extract_sent_token_spans(sent)
  token_idxs = find_in_array(token_spans, int(start_idx), int(end_idx))
  return token_idxs, [tokens[x] for x in token_idxs]


def extract_sbn_info(sent, sbn_raw_text):
  token_spans = extract_sent_token_spans(sent)
  collected_data = []
  clean_lines = [re.sub(' +', ' ', raw_line[5:]).replace('\n', '') for raw_line in sbn_raw_text.split('\n') if raw_line.startswith('%SBN%')]
  for idx, line in enumerate(clean_lines):
    line_data = EasyDict()
    collected_data.append(line_data)
    # combine multiwords name
    found_spaced_name = re.search('Name "[A-Za-z ]+"', line)
    if found_spaced_name is not None:
      text_to_replace = line[found_spaced_name.span()[0] + 5:found_spaced_name.span()[1]]
      replacement = text_to_replace.replace(' ', '_')
      line = line.replace(text_to_replace, replacement)
    info_blocks = [block.strip() for block in line.split('%')]
    sbn_parts = [item for item in info_blocks[0].split(' ')]
    line_data.sbn_word = sbn_parts[0]
    if line_data.sbn_word in SEPARATORS:
      line_data.sbn_word = None
      line_data.scope = list(sbn_parts)
    else:
      line_data.roles = [(sbn_parts[idx], sbn_parts[idx + 1]) for idx in range(1, len(sbn_parts), 2)] if len(sbn_parts) > 2 else []

      word_info_parts = info_blocks[1].split(' ')
      word_info = EasyDict()
      word_without_context = []
      word_with_context = []
      for part in word_info_parts:
        if part.startswith('--'):
          word_with_context.append(part)
        elif part.startswith('['):
          indices = part.strip()[1:-1].split('-')
          word_info.start_idx = int(indices[0])
          word_info.end_idx = int(indices[1])
          word_info.word_idxs = find_in_array(token_spans, word_info.start_idx, word_info.end_idx)
        else:
          word_without_context.append(part)
          word_with_context.append(part)
      word_info.word = ' '.join(word_without_context)
      word_info.word_with_context = ' '.join(word_with_context)

      line_data.word_info = word_info

  return collected_data


def map_sbn_integration(sbn_lines):
  integration_map = []
  context_map = []
  sbn_line_contents = []
  for line in sbn_lines:
    if line.sbn_word is not None:
      integration_center_name = line.sbn_word
      start_idx = None
      end_idx = None
      if len(line.roles) == 1 and (('+' not in line.roles[0][1] and '-' not in line.roles[0][1]) or len(line.roles[0][1]) == 1):
        integration_center_name += '_' + line.roles[0][0] + '_' + line.roles[0][1].replace('&gt;', '>').replace('&lt;', '<')
      if 'word_info' in line and 'start_idx' in line.word_info:
        start_idx = int(line.word_info.start_idx)
        end_idx = int(line.word_info.end_idx)
      # NOTE: sbn_line_contents content: sbn_word, token_span start_idx, token_span end_idx, token idxs, sbn_roles
      sbn_line_contents.append(
        (integration_center_name, start_idx, end_idx, line.word_info.word_idxs if 'word_idxs' in line.word_info else None, line.roles))
  idx = 0
  indent = 0
  connector_id = 0
  copy_sbn_lines = list(sbn_lines)
  while len(copy_sbn_lines) > 0:
    sbn_line = copy_sbn_lines.pop(0)
    if sbn_line.sbn_word is None:
      separator, connector = sbn_line.scope
      connector_sign = '<' if connector.startswith('&lt;') else '>'
      connector_value = int(connector[4:])
      indent += (2 - connector_value) if connector_value > 0 else 0
      connector_id += 1
      context_map.append((indent, connector_id, separator, connector_sign, connector_value))
    else:
      for role, value in sbn_line.roles:
        ori_token_span = None
        if 'word_info' in sbn_line and 'start_idx' in sbn_line.word_info:
          start_idx = int(sbn_line.word_info.start_idx)
          end_idx = int(sbn_line.word_info.end_idx)
          ori_token_span = (start_idx, end_idx)
        if '+' in value and len(value) > 1:
          target_idx = idx + int(value.replace('+', ''))
          integration_map.append((indent, connector_id, idx, role, target_idx, value, ori_token_span))
        if '-' in value and len(value) > 1:
          target_idx = idx - int(value.replace('-', ''))
          integration_map.append((indent, connector_id, idx, role, target_idx, value, ori_token_span))
      idx += 1

  return context_map, integration_map, sbn_line_contents, sbn_lines


def extract_sbn_integration(sent, sbn_raw_text):
  sbn_info = extract_sbn_info(sent, sbn_raw_text)
  return map_sbn_integration(sbn_info)


def clean_up_sbn_anas(sbn_anas_to_clean):
  result = []
  sorted_sbn_anas = sorted(sbn_anas_to_clean, key=lambda x: x[1])
  sbn_idxs = list(range(len(sorted_sbn_anas)))
  while len(sbn_idxs) > 0:
    sbn_ana_out = list(sorted_sbn_anas[sbn_idxs.pop(0)])
    copy_sbn_idxs = list(sbn_idxs)
    chain_idxs = [sbn_ana_out[4]]
    chain_distance = int(sbn_ana_out[6])
    while len(copy_sbn_idxs) > 0:
      current_idx = copy_sbn_idxs.pop(0)
      sbn_ana_in = list(sorted_sbn_anas[current_idx])
      if sbn_ana_in[4] in chain_idxs:
        sbn_ana_in[4] = sbn_ana_out[1]
        sbn_ana_in[5] = sbn_ana_out[2]
        sbn_ana_in[6] = int(sbn_ana_in[6]) - chain_distance
        chain_distance += sbn_ana_in[6]
        chain_idxs.append(sbn_ana_in[4])
        result.append(sbn_ana_out)
        sbn_ana_out = sbn_ana_in
        sbn_idxs.remove(current_idx)
    result.append(sbn_ana_out)

  return result


def replace_inner_box(full_semantic, box_name, prev_box_names):
  match = re.search(f'<({box_name})>([^/]*)</{box_name}>', full_semantic)
  inner_box = match.group()
  prev_box_names.insert(0, box_name)
  return full_semantic.replace(inner_box, f'__{"-".join(prev_box_names)}__'), match.groups()[1]


def extract_boxes(sem):
  box_contents = []
  box_names = re.findall('<(b\d)>', sem)
  boxes_found = []
  while len(box_names) > 0:
    box_name = box_names[0]
    outer_box = re.search(f'<({box_name})>(.*)</{box_name}>', sem)
    outer_content = outer_box.group()
    inner_boxes = re.findall('<(b\d)>', outer_content)
    if len(inner_boxes) > 1:
      replaced_box_names = []
      for inner_box_name in reversed(inner_boxes):
        sem, box_found = replace_inner_box(sem, inner_box_name, replaced_box_names)
        boxes_found.append(box_found)
        box_names.remove(inner_box_name)
    else:
      sem, box_found = replace_inner_box(sem, box_name, [])
      boxes_found.append(box_found)
      box_names.remove(box_name)

  for box_raw_content in boxes_found:
    box_contents += [x.split('←')[1] for x in ast.literal_eval(box_raw_content.split(']:')[1])]
  return box_contents, sem


def contains_resolution(item):
  return True in [x in item for x in RESOLUTION_SYMBOLS]


def categorize_predicates(sem_possible_predicates):
  collected_data = []
  non_time_preds = [x for x in sem_possible_predicates if not x.startswith('time:time.n.08')]
  is_noun = '.n.' in str(non_time_preds)
  for item in sem_possible_predicates:
    if item.startswith('time:time.n.08'):
      arg_start_idx = item.index('(')
      collected_data.append(('TIME', item[:arg_start_idx], item[arg_start_idx:]))
    elif ':' in item and '@' not in item:
      arg_start_idx = item.index('(')
      if is_noun:
        collected_data.append(('NOUN', item[:arg_start_idx], item[arg_start_idx:]))
      elif '.v.' in str(non_time_preds):
        collected_data.append(('VERB', item[:arg_start_idx], item[arg_start_idx:]))
      else:
        collected_data.append(('WORD', item[:arg_start_idx], item[arg_start_idx:]))
    elif is_noun and '(' in item:
      arg_start_idx = item.index('(')
      collected_data.append(('PROP', item[:arg_start_idx], item[arg_start_idx:]))
    elif '@' not in item and '(' in item:
      arg_start_idx = item.index('(')
      collected_data.append(('ROLE', item[:arg_start_idx], item[arg_start_idx:]))
    elif contains_resolution(item):
      collected_data.append(('RESOLUTION', item, None))
    else:
      collected_data.append(('STRUCTURE', item, None))
  return collected_data


def contains_cat_of(groups, cat, predicate):
  return predicate in [x[1] for idx, x in groups[cat]]


def contains_prop_of(groups, prop_predicate):
  return contains_cat_of(groups, 'PROP', prop_predicate)


def contain_non_resolving_noun(groups):
  if contains_prop_of(groups, 'PartOf'):
    preds = ['person:person.n.01', 'boy:boy.n.01', 'female:female.n.02', 'male:male.n.02', 'woman:woman.n.02', 'girl:girl.n.01', 'man:man.n.01']
    if groups['NOUN'][0][1][1] in preds:
      return True

  if contains_prop_of(groups, 'User') or contains_prop_of(groups, 'Owner') or contains_prop_of(groups, 'Creator') or contains_prop_of(groups, 'Of'):
    preds = ['person:person.n.01', 'female:female.n.02', 'male:male.n.02', 'man:man.n.01', 'friend:friend.n.01']
    if groups['NOUN'][0][1][1] in preds:
      return True

  if contains_prop_of(groups, 'Order') and groups['NOUN'][0][1][1] == 'rank:rank.n.02':
    return True

  if contains_prop_of(groups, 'Path') and groups['NOUN'][0][1][1] == 'entity:entity.n.01':
    return True

  if contains_cat_of(groups, 'NOUN', 'quantity:quantity.n.01'):
    return True

  if contains_prop_of(groups, 'QuantityOf'):
    return True

  # These are anaphora resolutions
  if contains_prop_of(groups, 'Equal') and groups['NOUN'][0][1][1] == 'person:person.n.01':
    return True

  # These are manual skipping
  if contains_cat_of(groups, 'NOUN', 'train:train.n.01') \
      or contains_prop_of(groups, 'AttributeOf'):
    return True


def contains_verb(groups):
  return len(groups['VERB']) > 0


def contains_noun(groups):
  return len(groups['NOUN']) > 0


def calculate_word_predicates(storage, elements, syntax_cat):
  calculated_storage_change = dict(e=0, r=0, p=0)
  groups = defaultdict(list)
  used_elements = []
  el_idx_to_remove = []

  for idx, el in enumerate(elements):
    cat, pred, args = el
    groups[cat].append((idx, el))

  # NOTE: Make the assumption that on continuation, the event will point back to previous dref and that the prop of that dref is already known
  if syntax_cat in ['conj', '(S/S)/S[dcl]', '((S\\NP)\\(S\\NP))/NP']:
    calculated_storage_change['e'] += 1
    calculated_storage_change['r'] += 1
    return used_elements, elements, calculated_storage_change

  # If the line is a verb
  if contains_verb(groups):
    pred = groups['VERB'][0][1][1]
    arg_start_idx = pred.index(':')
    verb_word = pred[:arg_start_idx]
    # modal words still requires an event without any roles being resolved
    # non_time_roles = [x for x in groups['ROLE'] if x[1][1] != 'Time'] # disabled because apparently ROLE==Time is necessary in some cases
    non_time_roles = groups['ROLE']
    if len(non_time_roles) > 1:
      calculated_storage_change['p'] += len(non_time_roles) - 1
    if verb_word not in MODAL_WORDS:
      if storage['e'] > 0:
        calculated_storage_change['e'] -= 1
        calculated_storage_change['r'] -= 1

        el_idx_to_remove.append(groups['VERB'][0][0])
        for role_idx, role_el in non_time_roles:
          el_idx_to_remove.append(role_idx)
      else:
        el_idx_to_remove.append(groups['VERB'][0][0])
        if len(groups['ROLE']) > 0:
          el_idx_to_remove.append(groups['ROLE'][0][0])

  # If the line is a noun
  elif contains_noun(groups):
    if not contain_non_resolving_noun(groups):
      el_idx_to_remove.append(groups['NOUN'][0][0])
      calculated_storage_change['p'] -= 1

  else:
    # non_time_roles = [x for x in groups['ROLE'] if x[1][1] != 'Time'] # disabled because apparently ROLE==Time is necessary in some cases
    non_time_roles = groups['ROLE']
    if len(non_time_roles) > 0:
      calculated_storage_change['p'] += 1

  for idx_to_remove in sorted(el_idx_to_remove, reverse=True):
    used_elements.append(elements[idx_to_remove])
    del elements[idx_to_remove]

  return used_elements, elements, calculated_storage_change


def count_storage_cost(storage):
  return storage['events'] + storage['roles'] + storage['properties']


def extract_lambda_info(enumerated_tokens, lambda_raw_text):
  sbntoken_semantic_list = []
  for lambda_block in lambda_raw_text.split('----------'):
    if lambda_block.strip() == '':
      continue
    lines = [x for x in lambda_block.split('\n') if len(x.strip()) > 0]
    sbntoken = lines[0][7:].strip()
    sem = lines[1][5:].strip()
    syntax_cat = lines[2][5:].strip()
    sbntoken_semantic_list.append((sbntoken, sem, syntax_cat))

  collected_data = []
  prev_sbntokens = []
  prev_full_sbntokens = []
  prev_sems = []
  last_enum_token = None
  storage_predicates = dict(
    e=1,
    r=1,
    p=1
  )

  for idx, (sbntoken, sem, syntax_cat) in enumerate(sbntoken_semantic_list):
    prev_sbntokens.append(sbntoken)
    prev_full_sbntokens.append(sbntoken)
    prev_sems.append(sem)
    if sbntoken == 'ø':
      del prev_sbntokens[-1]
      continue
    elif len(enumerated_tokens) > 1 \
        and (
        sbntoken_semantic_list[idx + 1][0].startswith("'")
        or (enumerated_tokens[0][1] == 'cannot' and sbntoken_semantic_list[idx + 1][0] == 'not')
        or (sbntoken_semantic_list[idx + 1][0] == "n't")
        or (sbntoken_semantic_list[idx + 1][0] == ",")
    ):
      continue
    elif len(enumerated_tokens) == 1 and enumerated_tokens[0][1].endswith('.') and sbntoken != '.':
      continue
    else:
      if enumerated_tokens[0][1] == ''.join(prev_sbntokens):
        last_enum_token = enumerated_tokens.pop(0)
      sent_token = last_enum_token[1]
      sem_possible_predicates = []
      simplified_sems = []
      for prev_sem in prev_sems:
        boxes, simplified_sem = extract_boxes(prev_sem)
        sem_possible_predicates += boxes
        simplified_sems.append(simplified_sem)

      token_drs_elements = categorize_predicates(sem_possible_predicates)
      used_elements, left_over_elements, calculated_change = calculate_word_predicates(storage_predicates, list(token_drs_elements), syntax_cat)
      storage_predicates['e'] += calculated_change['e']
      storage_predicates['r'] += calculated_change['r']
      storage_predicates['p'] += calculated_change['p']

      collected_data.append(
        (last_enum_token[0], sent_token, copy.deepcopy(storage_predicates), left_over_elements, used_elements, prev_full_sbntokens, syntax_cat,
         '<<>>'.join(simplified_sems), calculated_change))
      prev_sbntokens = []
      prev_full_sbntokens = []
      prev_sems = []

  return collected_data
