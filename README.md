This repository explores the relationship between words available in [JMDict](https://jedict.com/HTML/edict_doc.html) (probably the most widely-used source for Japanese-English dictionaries) and those available in various monolingual Japanese-Japanese dictionaries. Specifically, I use a subset of the monolingual dictionaries [shared](https://learnjapanese.link/dictionaries) on [TheMoeWay](https://learnjapanese.moe/monolingual/)), currently including (with modest re-naming):

1. `Monolingual_Onomatopoeia_surasura`
2. `Monolingual_三省堂国語辞典_第八版_Recommended`
3. `Monolingual_実用日本語現辞典_Extended_Recommended`
4. `Monolingual_新明解国語典_第八版_Recommended`
5. `Monolingual_日本語俗語書`
6. `Monolingual_旺文社国語辞典_第十一版_Recommended`
7. `Monolingual_明鏡国語辞典_第二版_Recommended_Improved`

This repository's primary motivation is that in a not-yet-public version of [my OCR-to-Anki-deck-building/Japanese sentence-miner project](https://github.com/NeverConvex/ocr_to_anki_public), I've added an offline version of JMDict (though, a version I -- with significant LLM-coding-assisted help -- ETL'd into, first, nested JSON, and then into a sequence of simple SQL databases) as an alternative source to Jisho, and have added automated insertion of monolingual definitions on the back sides of cards, whenever the token (word or expression) taken from JMDict/Jisho appears exactly in at least one of the above monolingual sources. The 'hit rate' on exact words and expressions is high enough to be useful for common words/expressions (though I haven't generated a numerical estimate for how often this seems to happen during my in-the-wild sentenec mining), but the actual proportion of exactly shared search tokens appears to be surprisingly low (≈10%, from memory; planning to update repo later with actual calculation/reusable code for it).

I found the 10% overlap surprisingly low. So, to determine if there are ways to improve over exact matching when identifying monolingual dictionary entries that correspond to any given JMDict/Jisho token, this repository currently houses code to:

1. find the search-term tokens in JMdict that are not present in any monolingual dictionary, monolingual dictionary tokens not in JMdict (finding the symmetric difference, but keeping the JMDict and monolingual dictionary contributions separate)
2. use sqlite3's optional edit-distance support via the [spellfix](https://www.sqlite.org/spellfix1.html) virtual table to find simple top-K edit-distance monolingual-dict tokens to each remaining JMDict token

Step 2, although much faster than the Japanese-conjugation-aware Python implementations of [Levenshtein distance](https://en.wikipedia.org/wiki/Levenshtein_distance) and [approximate string matching](https://en.wikipedia.org/wiki/Approximate_string_matching) I rely on to match searched terms with (image, OCR-text) pairs in [the main OCR sentence-miner project script](https://en.wikipedia.org/wiki/Levenshtein_distance), is still quite computation-and-time-intensive, so this repository additionally provides support in [`jmdict_monolingdict_token_mappings.executeMultiple`](https://github.com/NeverConvex/jmdict_monolingdict_token_mappings/blob/888e3a2f9f6cb8f0909cb17276883c0075fb7081/missingTokensEditDist.py#L255) for generating a simple (but based on R-square/thinking about how the edit-distance calculations are likely implemented in C under-the-hood of spellfix, probably completely adequate[^1]) regression-based prediction of full-scale run-time.

Once Step 2 is complete, I intend next to:

3. repeat similar calculations but using Japanese-conjugation-aware Levenshtein distance. I suspect/hope that, among the ≈90% of non-shared tokens, many actually appear to be identical or near-identical after accounting for various common Japanese-language transformations (like conjugating verbs; making different choices about whether to write a token in kanji, hiragana, or katakana; making common formal/informal substitutions e.g. swapping `と` with `って`, and so forth), and that the Levenshtein-distance calculations will hopefull be able to detect this without generating too many false positives (incorrectly applying transformations to suggest two tokens are identical when they are semantically different).

[^1]: e.g., a test calculation produces this output:
```
For 1000000 pairs, elapsed time (secs): 0.2392880916595459
# calcs -> elapsed_time
625 -> 0.0012416839599609375
2500 -> 0.002223491668701172
10000 -> 0.009378194808959961
250000 -> 0.08058786392211914
1000000 -> 0.2392880916595459
R-Square for predicting run-time from numcalcs: 0.9930411635712505
jmdict.db initially has tables: ['jmdict_slug', 'jmdict_japanese', 'jmdict_engl_defns', 'jmdict_pos', 'jmdict_tags', 'jmdict_attributions', 'distinct_jmdict_engl_defns_monoling_join', 'jm_spellfix', 'jm_spellfix_vocab']
jmdict pragma table_info: (0, 'id', 'INTEGER', 0, None, 1)
monol pragma table_info: None
jmremaining_tab contains 460290 rows
monolremaining_tab contains 98075 rows
For 45142941750 numcalcs, expected run-time: 10654.571062474555 secs
        (approx day:hour:mins: 2:57:34.571062)
```
