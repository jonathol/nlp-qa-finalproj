"""General utilities for training.

Author:
    Shrey Desai
"""

import os
import json
import gzip
import pickle

import torch
from tqdm import tqdm

# Task 1 stuff 
import spacy
nlp = spacy.load("en_core_web_sm")
from spacy.matcher import PhraseMatcher
matcher = PhraseMatcher(nlp.vocab)


def cuda(args, tensor):
    """
    Places tensor on CUDA device (by default, uses cuda:0).

    Args:
        tensor: PyTorch tensor.

    Returns:
        Tensor on CUDA device.
    """
    if args.use_gpu and torch.cuda.is_available():
        return tensor.cuda()
    return tensor


def unpack(tensor):
    """
    Unpacks tensor into Python list.

    Args:
        tensor: PyTorch tensor.

    Returns:
        Python list with tensor contents.
    """
    if tensor.requires_grad:
        tensor = tensor.detach()
    return tensor.cpu().numpy().tolist()


def load_dataset(path):
    """
    Loads MRQA-formatted dataset from path.

    Args:
        path: Dataset path, e.g. "datasets/squad_train.jsonl.gz"

    Returns:
        Dataset metadata and samples.
    """
    with gzip.open(path, 'rb') as f:
        elems = [
            json.loads(l.rstrip())
            for l in tqdm(f, desc=f'loading \'{path}\'', leave=False)
        ]
    meta, samples = elems[0], elems[1:]
    return (meta, samples)


def load_cached_embeddings(path):
    """
    Loads embedding from pickle cache, if it exists, otherwise embeddings
    are loaded into memory and cached for future accesses.

    Args:
        path: Embedding path, e.g. "glove/glove.6B.300d.txt".

    Returns:
        Dictionary mapping words (strings) to vectors (list of floats).
    """
    bare_path = os.path.splitext(path)[0]
    cached_path = f'{bare_path}.pkl'
    if os.path.exists(cached_path):
        return pickle.load(open(cached_path, 'rb'))
    embedding_map = load_embeddings(path)
    pickle.dump(embedding_map, open(cached_path, 'wb'))
    return embedding_map


def load_embeddings(path):
    """
    Loads GloVe-style embeddings into memory. This is *extremely slow* if used
    standalone -- `load_cached_embeddings` is almost always preferable.

    Args:
        path: Embedding path, e.g. "glove/glove.6B.300d.txt".

    Returns:
        Dictionary mapping words (strings) to vectors (list of floats).
    """
    embedding_map = {}
    with open(path) as f:
        next(f)  # Skip header.
        for line in f:
            try:
                pieces = line.rstrip().split()
                embedding_map[pieces[0]] = [float(weight) for weight in pieces[1:]]
            except:
                pass
    return embedding_map


def search_span_endpoints(start_probs, end_probs, args, context, question, ans_start, ans_end, window=15):
    """
    Finds an optimal answer span given start and end probabilities.
    Specifically, this algorithm finds the optimal start probability p_s, then
    searches for the end probability p_e such that p_s * p_e (joint probability
    of the answer span) is maximized. Finally, the search is locally constrained
    to tokens lying `window` away from the optimal starting point.

    Args:
        start_probs: Distribution over start positions.
        end_probs: Distribution over end positions.
        window: Specifies a context sizefrom which the optimal span endpoint
            is chosen from. This hyperparameter follows directly from the
            DrQA paper (https://arxiv.org/abs/1704.00051).

    Returns:
        Optimal starting and ending indices for the answer span. Note that the
        chosen end index is *inclusive*.
    """
    max_start_index = start_probs.index(max(start_probs))
    max_end_index = -1
    max_joint_prob = 0.
    


    if args.task == 1:
        '''
        print()
        print(args.task)
        print(' '.join(context))
        '''
        keep = {'PROPN', 'VERB', 'NOUN'}
        q = ' '.join(question)  
        '''
        print(q)    
        print("Answer: ", ' '.join(context[ans_start: ans_end+1]))  
        '''
        q = nlp(q)
        query = [token.text for token in q if token.pos_ in keep]
        #print(query)
        max_count = 0
        patterns = [nlp.make_doc(text) for text in query]
        matcher.add("AnswerList", patterns)

        document = nlp(' '.join(context))
        start_matches = matcher(document)

        start_idxs = [max_start_index]

        for m, m_idx_start, m_idx_stop in start_matches:
            if m_idx_stop + 15 + 1 > len(end_probs)-1 and len(start_probs[m_idx_stop:]) > 0:
                start_idxs.append(start_probs.index(max(start_probs[m_idx_stop:])))
            elif len(start_probs[m_idx_stop:m_idx_stop+window+1]) > 0:
                start_idxs.append(start_probs.index(max(start_probs[m_idx_stop:m_idx_stop+window+1])))

        '''
        if len(start_idxs) < 1:
            start_idxs[max_start_index]
        '''

        for s_idx in start_idxs:
            for end_index in range(len(end_probs)):
                if s_idx <= end_index <= s_idx + window:
                    joint_prob = start_probs[s_idx] * end_probs[end_index]
                    if joint_prob > max_joint_prob:
                        max_joint_prob = joint_prob
                        max_end_index = end_index
                        max_start_index = s_idx
        #print("My Answer: ", context[max_start_index:(max_end_index + 1)])
        #a
    else :        
        for end_index in range(len(end_probs)):
            if max_start_index <= end_index <= max_start_index + window:
                joint_prob = start_probs[max_start_index] * end_probs[end_index]
                if joint_prob > max_joint_prob:
                    max_joint_prob = joint_prob
                    max_end_index = end_index
        '''
        print()
        print("My Answer: ", context[max_start_index:(max_end_index + 1)])
        a
        '''
    

    return (max_start_index, max_end_index)
