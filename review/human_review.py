import pandas as pd
from typing import Optional

PROMPT = """
Options: [a]ccept  [e]dit  [r]eject  [s]kip  [q]uit
Enter choice: 
"""

def review_csv(input_csv: str,
               output_csv: str,
               text_column: str = "processed_text",
               original_ref_column: str = "original_text",
               auto_accept_threshold: float = 0.80,
               only_review_below: float = 0.80) -> Optional[pd.DataFrame]:
    """Interactive review of generated dataset.

    - Auto-accept rows with similarity >= auto_accept_threshold
    - Present rows with similarity < only_review_below for manual decisions
    - Save a reviewed CSV with columns: status, final_text, notes
    """
    df = pd.read_csv(input_csv)
    df['status'] = df.get('status', 'pending')
    df['final_text'] = df.get('final_text', df[text_column])
    df['notes'] = df.get('notes', '')

    # Auto-accept high-similarity rows
    if 'similarity' in df.columns:
        auto_mask = df['similarity'] >= auto_accept_threshold
        df.loc[auto_mask, 'status'] = 'accepted'
        df.loc[auto_mask, 'final_text'] = df.loc[auto_mask, text_column]

    # Iterate low-similarity rows
    to_review = df[(df['status'] == 'pending') & (df.get('similarity', 0) < only_review_below)]
    for idx, row in to_review.iterrows():
        print("\n" + "="*70)
        print(f"Original: {row.get(original_ref_column, '')}")
        print(f"Generated: {row[text_column]}")
        if 'similarity' in df.columns:
            print(f"Similarity: {row['similarity']}")
        if 'coverage' in df.columns:
            print(f"Coverage: {row['coverage']}")

        choice = input(PROMPT).strip().lower()
        if choice == 'q':
            break
        elif choice == 'a':
            df.at[idx, 'status'] = 'accepted'
            df.at[idx, 'final_text'] = row[text_column]
        elif choice == 'e':
            new_text = input("Edited text: ").strip()
            if new_text:
                df.at[idx, 'status'] = 'edited'
                df.at[idx, 'final_text'] = new_text
                df.at[idx, 'notes'] = (row.get('notes', '') or '') + ' (edited)'
            else:
                print("No changes made.")
        elif choice == 'r':
            df.at[idx, 'status'] = 'rejected'
        elif choice == 's':
            continue
        else:
            print("Unknown choice, skipping.")

    df.to_csv(output_csv, index=False)
    print(f"Reviewed dataset saved to {output_csv}")
    return df
