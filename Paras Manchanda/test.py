import pandas as pd

# Suppose df1 might be None
df1 = None
df2 = pd.DataFrame({'B': [4, 5]})
df3 = pd.DataFrame({'C': [7]})

# List to hold DataFrames and spacers
df_list = []

# Function to add DataFrame and empty spacer
def add_df_and_spacer(df, next_df):
    if df is not None:
        df_list.append(df)
        # Determine the length for the spacer based on current and next DataFrame
        if next_df is not None:
            length = max(len(df), len(next_df))
        else:
            length = len(df)
        # Add spacer DataFrame
        df_list.append(pd.DataFrame({'': [''] * length}))

# Add df1 and its spacer
add_df_and_spacer(df1, df2)

# Add df2 and its spacer
add_df_and_spacer(df2, df3)

# Add df3 without a following spacer
if df3 is not None:
    df_list.append(df3)

# Concatenate all the DataFrames and spacers if the list is not empty
if df_list:
    df_concatenated = pd.concat(df_list, axis=1)
    # Replace NaN values with empty string
    df_concatenated.fillna('', inplace=True)
    print(df_concatenated)
else:
    print("No DataFrames to concatenate.")
