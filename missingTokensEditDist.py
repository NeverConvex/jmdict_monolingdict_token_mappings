# Standard libraries (NOTE sqlite also has a non-standard sqlfix installation and required .so)
import sqlite3, time, datetime

# Non-standard libraries
import fire
import numpy as np
from sklearn.linear_model import LinearRegression   

def findMissingTokens(limit=-1):
    """
        Creates columns containing tokens only in jmdict (engl_defns), and tokens only in monoling dictionaries.
    """
    conn = sqlite3.connect("jmdict.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table';
    """)
    jmd_tables = [row[0] for row in cur.fetchall()]
    print(f"jmdict.db initially has tables: {jmd_tables}")

    cur.execute("""
    ATTACH DATABASE 'monolingual_dicts.db' AS monoling;
    """)

    #monol_tables = cur.execute("""
    #    SELECT name
    #    FROM monoling
    #    WHERE type='table';
    #""").fetchall()
    #print(f"Attached monolingual_dicts.db, with tables: {monol_tables}")

    jmd_pragma_info = cur.execute("PRAGMA table_info(jmdict_engl_defns);").fetchone()
    monol_pragma_info = cur.execute("PRAGMA table_info(monoling)").fetchone()
    print(f"jmdict pragma table_info: {jmd_pragma_info}")
    print(f"monol pragma table_info: {monol_pragma_info}")

    # Create temp table containing tokens in jmdict_engl_defns not found in any monolingual dict
    cur.execute(f"""
        CREATE TEMP TABLE jmremaining_tab AS
        WITH symdiff AS (
            SELECT token FROM jmdict_engl_defns
            UNION
            SELECT word_or_expr FROM monolingual_dicts

            EXCEPT

            SELECT token FROM jmdict_engl_defns
            INTERSECT
            SELECT word_or_expr FROM monolingual_dicts
        ),
        jmremaining AS (
            SELECT token FROM jmdict_engl_defns
            EXCEPT
            SELECT * FROM symdiff
        )
        SELECT *
        FROM jmremaining
        LIMIT {limit};
    """)

    jmd_numrows = cur.execute("""
        SELECT COUNT(*)
        FROM jmremaining_tab;
    """).fetchone()[0]
    print(f"jmremaining_tab contains {jmd_numrows} rows")

    # Create temp table containing tokens in any monolingual dict not found in jmdict_engl_defns
    # TODO 8/1/2026 may as well convert symdiff to a temp table to avoid repeating the calculation
    cur.execute(f"""
        CREATE TEMP TABLE monolremaining_tab AS
        WITH symdiff AS (
            SELECT token FROM jmdict_engl_defns
            UNION
            SELECT word_or_expr FROM monolingual_dicts

            EXCEPT

            SELECT token FROM jmdict_engl_defns
            INTERSECT
            SELECT word_or_expr FROM monolingual_dicts
        ),
        monoremaining AS (                                                        
            SELECT word_or_expr FROM monolingual_dicts
            EXCEPT                                                                
            SELECT * FROM symdiff                                                 
            )
        SELECT *
        FROM monoremaining
        LIMIT {limit};
    """)
    monol_numrows = cur.execute("""
        SELECT COUNT(*)
        FROM monolremaining_tab;
    """).fetchone()[0]
    print(f"monolremaining_tab contains {monol_numrows} rows")
    conn.commit()

    return conn, cur, jmd_numrows, monol_numrows

def getFullScaleNumCalcs():
    """
        Creates columns containing tokens only in jmdict (engl_defns), and tokens only in monoling dictionaries.
    """
    conn = sqlite3.connect("jmdict.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table';
    """)
    jmd_tables = [row[0] for row in cur.fetchall()]
    print(f"jmdict.db initially has tables: {jmd_tables}")

    cur.execute("""
    ATTACH DATABASE 'monolingual_dicts.db' AS monoling;
    """)

    jmd_pragma_info = cur.execute("PRAGMA table_info(jmdict_engl_defns);").fetchone()
    monol_pragma_info = cur.execute("PRAGMA table_info(monoling)").fetchone()
    print(f"jmdict pragma table_info: {jmd_pragma_info}")
    print(f"monol pragma table_info: {monol_pragma_info}")

    # Create temp table containing tokens in jmdict_engl_defns not found in any monolingual dict
    cur.execute(f"""
        CREATE TEMP TABLE jmremaining_tab AS
        WITH symdiff AS (
            SELECT token FROM jmdict_engl_defns
            UNION
            SELECT word_or_expr FROM monolingual_dicts

            EXCEPT

            SELECT token FROM jmdict_engl_defns
            INTERSECT
            SELECT word_or_expr FROM monolingual_dicts
        ),
        jmremaining AS (
            SELECT token FROM jmdict_engl_defns
            EXCEPT
            SELECT * FROM symdiff
        )
        SELECT *
        FROM jmremaining;
    """)

    jmd_numrows = cur.execute("""
        SELECT COUNT(*)
        FROM jmremaining_tab;
    """).fetchone()[0]
    print(f"jmremaining_tab contains {jmd_numrows} rows")

    # Create temp table containing tokens in any monolingual dict not found in jmdict_engl_defns
    # TODO 8/1/2026 may as well convert symdiff to a temp table to avoid repeating the calculation
    cur.execute(f"""
        CREATE TEMP TABLE monolremaining_tab AS
        WITH symdiff AS (
            SELECT token FROM jmdict_engl_defns
            UNION
            SELECT word_or_expr FROM monolingual_dicts

            EXCEPT

            SELECT token FROM jmdict_engl_defns
            INTERSECT
            SELECT word_or_expr FROM monolingual_dicts
        ),
        monoremaining AS (                                                        
            SELECT word_or_expr FROM monolingual_dicts
            EXCEPT                                                                
            SELECT * FROM symdiff                                                 
            )
        SELECT *
        FROM monoremaining;
    """)
    monol_numrows = cur.execute("""
        SELECT COUNT(*)
        FROM monolremaining_tab;
    """).fetchone()[0]
    print(f"monolremaining_tab contains {monol_numrows} rows")
    conn.commit()

    return jmd_numrows * monol_numrows

def getClosestByEditDist(conn, cur, jmd_numrows, monol_numrows, num_dists_limit=5):
    conn.enable_load_extension(True)
    spellfix_path = open("spellfix_path.txt", 'r').readline().strip()
    conn.load_extension(spellfix_path)

    cur.execute("DROP TABLE IF EXISTS jm_spellfix;")
    conn.commit()
    cur.execute("CREATE VIRTUAL TABLE jm_spellfix USING spellfix1;")
    conn.commit()

    cur.execute("""
        INSERT INTO jm_spellfix(word, rank, langid)
        SELECT token, 1, 0
        FROM jmremaining_tab;
    """)

    # NOTE progress_handler seems to interrupt the editdist calculation
    #def progress():
    #    global counter
    #    counter += 1
    #    if counter % 100 == 0:
    #        print(f"SQLite VM steps: {counter}")
    #    return 0 # return nonzero to abort the query

    print(f"Beginning edit-distance calculations (this may take a while)...")
    #conn.set_progress_handler(progress, 1)
    # TODO 8/1/2026 move this to a separate thread so we can jury-rig a progress timer
    t0 = time.time()
    cur = conn.cursor()
    res = cur.execute(f"""
    SELECT
        monolremaining_tab.word_or_expr AS word_or_expr,
        (
            SELECT json_group_array(
                json_object(
                    'match', word,
                    'distance', distance
                    )
             )
           FROM
            (
            SELECT word, distance
            FROM jm_spellfix
            WHERE word MATCH monolremaining_tab.word_or_expr
            ORDER BY distance
            LIMIT {num_dists_limit}
            ) 
        )
        AS closest_matches 
    FROM monolremaining_tab;
    """).fetchall()
    elapsed_time, num_calcs = time.time() - t0, jmd_numrows * monol_numrows
    conn.commit()

    print(f"Distance calculations result:")
    for r in res:
        print(f"\t{r}")

    print(f"For {num_calcs} pairs, elapsed time (secs): {elapsed_time}")
    #print(f"counter: {counter}")
    return elapsed_time, num_calcs

def execute(limit=25):
    conn, cur, jmd_numrows, monol_numrows = findMissingTokens(limit=limit)
    _, _ = getClosestByEditDist(conn, cur, jmd_numrows, monol_numrows)
  

def executeMultiple(limits=[], pred_numcalcs=0, pred_fullscaleruntime=True):
    timing_info = []
    for l in limits:
        conn, cur, jmd_numrows, monol_numrows = findMissingTokens(limit=l)
        elapsed_time, num_calcs = getClosestByEditDist(conn, cur, jmd_numrows, monol_numrows)
        timing_info.append( (num_calcs, elapsed_time) )
    print("# calcs -> elapsed_time")
    for n, t in timing_info:
        print(f"{n} -> {t}")

    if pred_numcalcs or pred_fullscaleruntime:
        X, y = [[xy[0]] for xy in timing_info], [xy[1] for xy in timing_info]
        reg = LinearRegression().fit(X, y)
        rsquare = reg.score(X, y) 
        print(f"R-Square for predicting run-time from numcalcs: {rsquare}")

    if pred_numcalcs:
        predicted_runtime = reg.predict(np.array([[pred_numcalcs]]))[0]
        print(f"For {pred_numcalcs} numcalcs, expected run-time: {predicted_runtime} secs")

    if pred_fullscaleruntime:
        fullscale_numcalcs = getFullScaleNumCalcs()
        predicted_runtime = reg.predict(np.array([[fullscale_numcalcs]]))[0]
        print(f"For {fullscale_numcalcs} numcalcs, expected run-time: {predicted_runtime} secs")
        print(f"\t(approx day:hour:mins: {datetime.timedelta(seconds=predicted_runtime)})")

def main():
    raise NotImplementedError(f"This script is meant to be called via Fire, e.g.:\t\npython missingTokensEditDist.py execute --limit=50")

if __name__ == "__main__":
    fire.Fire()
