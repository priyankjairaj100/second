"""Whole last-word scoring contract. No model or corpus is loaded here."""
import math


def prepare_last_word(text, encode, max_sequence_length):
    if type(text) is not str or ' ' not in text:
        raise ValueError('text must contain context and a final space-separated word')
    if type(max_sequence_length) is not int or max_sequence_length<2:
        raise ValueError('invalid model position limit')
    context,word=text.rsplit(' ',1)
    if not word:
        raise ValueError('empty last word')
    prefix=tuple(encode(context));target=tuple(encode(' '+word));full=tuple(encode(text))
    if full!=prefix+target:
        raise ValueError('tokenization crosses the context-target boundary')
    if not prefix or not target or any(type(t) is not int or t<0 for t in full):
        raise ValueError('invalid context or target tokens')
    # Last target token needs no input position. Retain enough context for all predictions.
    keep=max_sequence_length-len(target)+1
    if keep<1:
        raise ValueError('target exceeds the position budget')
    retained=prefix[-keep:]
    return {'context':retained,'target':target,'dropped_context_tokens':len(prefix)-len(retained),
            'input_tokens':retained+target[:-1]}


def score_last_word(prepared, logits):
    context=tuple(prepared['context']);target=tuple(prepared['target'])
    inputs=tuple(prepared['input_tokens'])
    if not context or not target or inputs!=context+target[:-1]:
        raise ValueError('invalid prepared last-word input')
    if len(logits)!=len(inputs):
        raise ValueError('one logit row per input token is required')
    selected=logits[len(context)-1:]
    if len(selected)!=len(target):
        raise ValueError('target prediction alignment differs')
    total=0.0;greedy=[]
    width=len(selected[0])
    for row,token in zip(selected,target):
        if (len(row)!=width or width<1 or type(token) is not int or not 0<=token<width
                or any(type(x) not in (int,float) or not math.isfinite(x) for x in row)):
            raise ValueError('invalid logits or target vocabulary')
        peak=max(row)
        total+=row[token]-peak-math.log(math.fsum(math.exp(x-peak) for x in row))
        greedy.append(max(range(width),key=lambda i:(row[i],-i)))
    return {'word_correct':tuple(greedy)==target,'target_tokens':len(target),
            'log_likelihood':total,'target_predictions':tuple(greedy),
            'dropped_context_tokens':prepared['dropped_context_tokens'],
            'log_likelihood_is_certified_interval':False}
