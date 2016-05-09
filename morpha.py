"""
Wrapper around morpha from
http://www.informatics.sussex.ac.uk/research/groups/nlp/carroll/morph.html

Vaguely follows edu.stanford.nlp.Morphology except we implement with a pipe.
hacky.  Would be nice to use cython/swig/ctypes to directly embed morpha.yy.c
as a python extension.

TODO compare linguistic quality to lemmatizer in python's "pattern" package

By Brendan O'Connor (http://brenocon.com), at https://gist.github.com/brendano/6008945
"""

import os,subprocess

#MorphaDir = os.path.join(os.path.dirname(__file__), 'morph')
MorphaDir = 'morph'
MorphaCmd = os.path.join(MorphaDir, 'morpha')
MorphaArgs= ['-f', os.path.join(MorphaDir, 'verbstem.list')]

_pipe = None

def get_pipe():
    global _pipe
    if _pipe is None:
        open_pipe()
    elif _pipe.returncode is not None:
        print "Pipe seems to have died, restarting"
        open_pipe()
    return _pipe

def open_pipe():
    global _pipe
    print "Opening morpha pipe"
    _pipe = subprocess.Popen([MorphaCmd] + MorphaArgs, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

def process(input):
    input = input.strip()
    output = None
    for retry in range(3):
        try:
            pipe = get_pipe()
            print>>pipe.stdin, input
            pipe.stdin.flush()
            output = pipe.stdout.readline()
        except IOError:
            if retry==2: raise
            print "Retry on pipe breakage"
            open_pipe()
    return output.rstrip('\n')


## From morph/doc.txt....

#Where the -u option is not used, each input token is expected to be of
#the form <word>_<tag>. For example:
#
#   A_AT1 move_NN1 to_TO stop_VV0 Mr._NNS Gaitskell_NP1 from_II nominating_VVG
#
#Contractions and punctuation must have been separated out into separate
#tokens. The tagset is assumed to resemble CLAWS-2, in the following
#respects:
#
#   V...      all verbs
#   NP...     all proper names
#   N[^P]...  all common nouns
#
#and for specific cases of ambiguous lexical items:
#
#   'd_VH...  root is 'have'
#   'd_VM...  root is 'would'
#   's_VBZ... root is 'be'
#   's_VHZ... root is 'have'
#   's_$...   possessive morpheme (also _POS for CLAWS-5)
#   ai_VB...  root is 'be'
#   ai_VH...  root is 'have'
#   ca_VM...  root is 'can'
#   sha_VM... root is 'shall'
#   wo_VM...  root is 'will'
#   n't_XX... root is 'not'

def ptb_is_proper(ptb):
    return ptb in ('NP','NNP','NNPS')

def ptb2morphtag(ptb):
    ptb = ptb.upper()
    if ptb.startswith('V'):
        return 'V'
    if ptb_is_proper(ptb):
        return 'NP'
    if ptb.startswith('N'):
        return 'N'
    if ptb == 'MD':
        return 'V'   # um is this right?  it looks like it can take incomplete versions...
    if ptb == 'POS':
        return '$'
    return ''

def lemmatize_seq(words_and_pos, tagset='PENN'):
    """List of (word,pos) pairs.  Words are Unicode strings.
    Returns list of lemma strings."""
    assert tagset=='PENN', "don't support different tagsets yet"

    # Decorate the input pairs into one big string that morpha wants,
    # Run morpha,
    # Then undecorate the output.

    goods = [i for i in range(len(words_and_pos)) if words_and_pos[i][0]]
    escape_str = '..axsxdxfxqxwxexr..'
    new_pairs = []
    #for word,pos in words_and_pos:
    for i in goods:
        word,pos = words_and_pos[i]
        assert ' ' not in word
        word = word.replace('_', escape_str)
        morph_tag = ptb2morphtag(pos)
        new_pairs.append((word, morph_tag))
    decorated_input = u' '.join(u'{}_{}'.format(word,tag) if tag else word for word,tag in new_pairs)
    decorated_input = decorated_input.encode('utf8') # TODO is morpha utf8 safe?
    #print "INPUT", decorated_input
    result = process(decorated_input)
    #print "RESULT", result

    lemma_results = []
    result_tokens = result.split()
    assert len(result_tokens) == len(new_pairs)
    for i,lemma in enumerate(result_tokens):
        lemma = lemma.split('_')[0]    # Rare. I think this is a bug in morpha
        #assert '_' not in lemma
        lemma = lemma.decode('utf-8','replace') # TODO is morpha utf8 safe?
        lemma = lemma.replace(escape_str, '_')
        if not ptb_is_proper(words_and_pos[i][1]):
            lemma = lemma.lower()
        lemma_results.append(lemma)

    # juxtapose it back in
    final_results = ['' for x in range(len(words_and_pos))]
    for i,lemma in enumerate(lemma_results):
        final_results[goods[i]] = lemma
    return final_results

def lemmatize(word,pos, tagset='PENN'):
    seq = [(word,pos)]
    result = lemmatize_seq(seq, tagset=tagset)
    return result[0]
