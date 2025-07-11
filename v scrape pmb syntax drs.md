v scrape pmb syntax drs
v send jakub scraped data
v compare reading time with SBN distance
check lasha comment with jakub


4-4-2025
spillover in anaphora resolutions
measure interference by counting entities between integrations
distance vs reading time

13-5-2025
avg data analysis - linear regression
raw data analysis - mixed effect model

collect co-variant data
SUBTLEX UK

21-5-2025
scikit learn package for measure
collect raw data
share the analysis / jupyter


4-6-2025
** recheck the sbn without the proper order words

eye tracking data collection
gopass time / first time
second pass time / rereading time
see using regression if people go back
skipping rate of words


11-6-2025

ET skipping rate (yes / no) as dep ~ distance
ET non skipped RT as dep ~ distance
ET spill on both skip & non skipped

SPR + ET unresolved ana RT ~ resolved/unresolved + word_pos

thematic roles



20-6-2025
finish analysis
- Make sure 1 verb has 1 role to analyze (the closest/furthest) + number of roles with minus distance
- do storage cost analysis on anaphora resolutions & unresolved predicates with limit of the first number of words in the sent

create summary and send to jakub: with explanations of steps


4-7-2025
- add tvalues * p values
Done

- add C(reflexive) to skipped C(resolved)
This shows the same result as before. Targets tend to be not skipped when anaphora is resolved. Spill do not show any significance.

- exclude C(reflexive)==TRUE to skipped C(resolved)
This gives the same result as the previous point

- skip the first and last words
Some effects are less intense, but still significant

- weird data on et, so check the means
Nothing remarkable. The mean of data seems to be around 0.5, so nothing is wrong. min = 0, max = 1


- manual data analysis as benchmark


- use verb's prev roles and next roles as fixed effect + spill over of verbs


11-7-2025

- manual data analysis as benchmark

- include sent_pos as 'C(resolved) * sent_pos'
- subset 20% of the first sent_pos for each participant
- excude Time role out of storage analysis

- revisit statistics for linguists by Winter to explain the models & results
