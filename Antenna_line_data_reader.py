# 1.8.2023

import pandas as pd
import openpyxl
import numpy as np
import plotly.graph_objects as go
import re
import tkinter as tk
import tkinter.filedialog as filedialog
from tkinter import messagebox

DATAFRAMES = ['VSWR','RTWP','RSSI','ETP'] 
DATETIME_FORMAT_CSV = '="%d.%m.%Y %H:%M:%S"'
DATETIME_FORMAT_XLXS = '%d.%m.%Y %H:%M:%S'
SEPARATOR = ','

def parse_config(config, parameter : str, is_int : bool = False, is_bool : bool = False):
    '''
    parse_config: Function for parsing config, splits the value at # sign and converts the value to a certain type according to parameters

    param: config; ConfigParser object
    param: parameter; string, the name of the parameter in the config file
    param: is_int; boolean, True if the value of the parameter in config file is supposed to be int, 
                            False else 
    param: is_int; boolean, True if the value of the parameter in config file is supposed to be boolean, 
                            False else 
    '''
    if(is_int):
        return int(config['CONFIG'][parameter].split('#')[0].strip())
    elif(is_bool):
        return bool(config['CONFIG'][parameter].split('#')[0].strip())
    else:
        return config['CONFIG'][parameter].split('#')[0].strip()
    
def infer_datetime_format(dt_str): # Infer the datetime format based on the datetime string content in the dataframe
        if dt_str.startswith('="'):
            return DATETIME_FORMAT_CSV
        return DATETIME_FORMAT_XLXS

class DataReader:
    def __init__(self,dataframe_names):
        self.dataframe_names = dataframe_names
        self.dataframe_dict = {}
        self.selected_files = []
        self.init_gui()

    def init_gui(self): # Initializes all the tkinter GUI elements
        self.root = tk.Tk()
        self.root.title("Antennaline data visualizer")

        self.num_files_label = tk.Label(self.root, text="Enter number of files (leave blank for 1):")
        self.num_files_label.pack()
        self.num_files_input = tk.Entry(self.root)
        self.num_files_input.pack()

        self.select_files_button = tk.Button(self.root, text="Select Files", command=self.select_files)
        self.select_files_button.pack()
        
        self.rmod_label = tk.Label(self.root, text="Enter radios (e.g., '1,4,5' or leave blank for all):")
        self.rmod_label.pack()
        self.rmod_input = tk.Entry(self.root)
        self.rmod_input.pack()

        self.antenna_label = tk.Label(self.root, text="Enter antennas for radios  (e.g., '1,2;2,3;' or leave blank for all):")
        self.antenna_label.pack()
        self.antenna_label = tk.Label(self.root, text="; separator is used for differentiating antennas between different radios")
        self.antenna_label.pack()
        self.antenna_input = tk.Entry(self.root)
        self.antenna_input.pack()

        self.vswr_button = tk.Button(self.root, text="VSWR", command=lambda: self.plot_data('VSWR'))
        self.vswr_button.pack()
        
        self.rtwp_button = tk.Button(self.root, text="RTWP", command=lambda: self.plot_data('RTWP'))
        self.rtwp_button.pack()
        
        self.rssi_button = tk.Button(self.root, text="RSSI", command=lambda: self.plot_data('RSSI'))
        self.rssi_button.pack()
        
        self.etp_button = tk.Button(self.root, text="ETP", command=lambda: self.plot_data('ETP'))
        self.etp_button.pack()


        self.root.mainloop()
        
    def open_file(self, filename_path, filename):
        try:
            # Skipping the first row of the data
            if filename_path.endswith(".csv"):
                df = pd.read_csv(filename_path, skiprows=1, sep=SEPARATOR)
            elif filename_path.endswith(".xlsx"):
                df = pd.read_excel(filename_path, engine='openpyxl', skiprows=1)

            df_split_index_dict = {}
            for value in DATAFRAMES:
                self.find_df_split_index(df, value, df_split_index_dict)
            self.split_dataframes(df, df_split_index_dict, filename)

            return True
        except Exception as e:
            ext = '.xlsx' if filename_path.endswith('.xlsx') else '.csv'
            if ext == '.csv':
                messagebox.showerror("Error", f"An error occurred while opening the file: {filename+ext}\n{e}\nMake sure that the raw csv file was not modified!")
            else:
                messagebox.showerror("Error", f"An error occurred while opening the file: {filename+ext}\n{e}\n")
            print(f"An error occurred while opening the file: {e}")
            return False
        
    def find_df_split_index(self, df, name, dict): # Finds the indexes, in order to split the csv into separate dataframes
        if name == 'VSWR':
            dict[name] = 0
        else:
            dict[name] = df[df['Radio module'].str.contains(name, case=False, na=False)].index[0]

    def split_dataframes(self, df, split_dict, filename): # Splits the dataframes 
        key_index = 0
        self.dataframe_dict[filename] = {} # A new datastrure for storing dataframes insidea dict under a certain filename
        for key in self.dataframe_names:
            if key_index == 0:
                new_dataframe = df.loc[:split_dict[self.dataframe_names[key_index + 1]] - 1, :] # Split the first dataframe 
            elif key_index == len(self.dataframe_names) - 1:
                new_dataframe = df.loc[split_dict[self.dataframe_names[key_index]] + 1:, :] # Split the last dataframe
            else:
                new_dataframe = df.loc[split_dict[self.dataframe_names[key_index]] + 1:split_dict[self.dataframe_names[key_index + 1]] - 1, :] # Split the middle datafrmames

            if new_dataframe.applymap(lambda x: 'No data available' in str(x)).any().any(): # If the dataframe has this, it is empty
                continue
            elif key_index != 0: # If not the first dataframe, adjust the first row of the dataframe to be the header row and reset index
                new_dataframe.columns = new_dataframe.iloc[0]
                new_dataframe = new_dataframe[1:]
                new_dataframe = new_dataframe.reset_index(drop=True)

            self.dataframe_dict[filename][key] = new_dataframe # Store the dataframe
            key_index += 1
    
    def select_files(self):
        input = self.num_files_input.get() # Get the number of files input
        if not all(c.isdigit() for c in input):
            messagebox.showerror("Error", "The number of files input field contains something else than numbers!") 
            return
        elif input == "":
            num_files = 1
        else:
            num_files = int(input)
        if num_files > 3: # If input number was larger than 3, make sure that it was purposefully selected
            if messagebox.askokcancel("Are you sure?", f"Are you sure you want to select {num_files} files?"):
                pass
            else:
                return
        self.selected_files = [] # Clear previously selected files if any
        for _ in range(num_files):
            filename = filedialog.askopenfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv"), ("Excel Files", "*.xlsx")])
            if filename.endswith(".csv"):
                with open(filename, 'r') as file:
                    first_line = file.readline().strip()
                    # If the values VSWR not in the first line, then the file is invalid
                    if "VSWR" not in first_line:
                        messagebox.showerror("Error", "The selected file is invalid, file skipped!")
                        continue
                    else:
                        messagebox.showinfo("Success", "File accepted")
            elif filename.endswith(".xlsx"):
                try:
                    df = pd.read_excel(filename, engine='openpyxl', nrows=1)  # Read only the first row to check
                    # If the values VSWR not in the first column, then the file is invalid
                    if "VSWR" not in df.columns:
                        messagebox.showerror("Error", "The selected file is invalid, file skipped!")
                        continue
                    else:
                        messagebox.showinfo("Success", "File accepted")
                except Exception as e:
                    messagebox.showerror("Error", f"Error reading the file: {e}")
                    continue
            self.selected_files.append(filename)
        self.num_files_input.delete(0, tk.END) # Empty the input field

    def plot_data(self, name):
        if not self.selected_files:
            messagebox.showerror("Error", "No files selected")
            return

        filenames = [self.extract_filename(file) for file in self.selected_files]

        for filename_path in self.selected_files: # Iterate over selected file paths
            filename = self.process_filename(self.extract_filename(filename_path)) # Split the filename from the path
            if self.open_file(filename_path, filename): # Open the file and store dataframes
                pass
            else:
                print(f"An error occured while opening/reading the file {filename}")
                return
            
        # Read the input fields
        rmod_filter, antenna_filter_list = self.parse_filter_inputs()
        rmod_to_antenna = dict(zip(rmod_filter, antenna_filter_list))

        fig = go.Figure() # Creates the new graph figure
        first_timestamps = []
        filenames_in_order = []
        max_time_value = 0
        dataframes_empty = True

        for order_num, filename in enumerate(filenames, 1): # Loop thru the filenames
            processed_filename = self.process_filename(filename)
            if name not in self.dataframe_dict[processed_filename]: # Check that the dataframe by the name exists
                continue

            # Get the dataframe by the given name from the dict
            df = self.dataframe_dict[processed_filename][name]
            # Drops the na values form the dataframe
            df = df.dropna(axis=1, how='all')

            filenames_in_order.append(processed_filename)
            # Get details from the dataframe
            time_datapoints, first_timestamp, rmod_column_name, second_column_name = self.get_data_details(df, name)
            first_timestamps.append(first_timestamp)

            if max_time_value < max(max_time_value, time_datapoints[-1]): # Keep track of the max_time_value across the dataframes in different files
                    max_time_value = max(max_time_value, time_datapoints[-1])

            # Filter the rmods 
            if rmod_filter:
                df = self.filter_dataframe(df, rmod_filter, rmod_column_name)
            
            # Loop thru the unique rmods after the filteration
            for rmod in df[rmod_column_name].unique():
                rmod_df = df[df[rmod_column_name] == rmod]

                if name != 'ETP':
                    antenna_filter = self.get_antenna_filter_for_rmod(rmod, rmod_to_antenna) # Filter the antennas for the given rmod
                    if antenna_filter:
                        rmod_df = rmod_df[rmod_df[second_column_name].apply(lambda x: any(antenna in x for antenna in antenna_filter))]
                    else:
                        pass
                        #print(f"Graphing all antennas for {rmod}")

                rmod_df = rmod_df[~rmod_df.iloc[:, 3:].applymap(lambda x: x == '-').all(axis=1)] # Remove rows that have no values but '-'

                if not rmod_df.empty: # If rmod dataframe is not empty after processes, plot it
                    dataframes_empty = False
                    filename = self.process_filename(filename)
                    self.plot_rmod(rmod_df, time_datapoints, rmod_column_name, second_column_name, name, fig, first_timestamps, filename, filenames_in_order, order_num, max_time_value)

        # If variable dataframes_empty was False, then show the figure, else, do not show because no dataframes were drawn into the figure
        if not dataframes_empty:
            fig.show()
        else:
            messagebox.showerror("Error", "The selected file(s) do not contain this datafield")

    def extract_filename(self, file_path): # Extracts the filename from the path from the file
        return file_path.split('/')[-1].split('.')[0]

    def parse_filter_inputs(self): # Reads and parses the radio and antenna input fields
        rmod_input = self.rmod_input.get().replace(' ', '')
        antenna_input = self.antenna_input.get().replace(' ', '')

        if not all(c.isdigit() or c in [',', ';'] for c in rmod_input) or not all(c.isdigit() or c in [',', ';'] for c in antenna_input):
            messagebox.showerror("Error", f"Invalid input!\n The input field(s) contain something else than numbers, commas or semicolons")
            return [], []
        
        # Parse the rmod and antenna filteration data from the input fields
        rmod_filter = ["RMOD-" + item.strip() + "/" for item in rmod_input.split(',') if item.strip()]
        antenna_filter_parts = [part for part in antenna_input.split(';') if part]
        antenna_filter_list = [part.split(',') for part in antenna_filter_parts]

        return rmod_filter, antenna_filter_list

    def process_filename(self, filename): # If the filename is the original, which WebEM returns, extract BTS id and time from it
        if "ANTL" in filename:
            partial_filename = filename[15:]
            return partial_filename[:partial_filename.find("_")] + ":" + partial_filename[-4:]
        return filename

    def get_data_details(self, df, name): # Gets the time datapoints from the dataframe and sets the second_column_name according to dataframe name
        if name == 'ETP':
            columns_start = 2
            second_column_name = "Cells"
        else:
            columns_start = 3
            second_column_name = "Antenna/Port"

        time_datapoints = df.columns[columns_start:].tolist() # Make the time datapoints from the header row into a list
        first_timestamp = pd.to_datetime(df.columns[columns_start], format=infer_datetime_format(df.columns[columns_start])).strftime('%d.%m.%Y %H:%M:%S') # Get the first time datapoint
        rmod_column_name = "Radio module"
        formatted_timepoints = pd.Series(pd.to_datetime(time_datapoints, format=infer_datetime_format(df.columns[columns_start]))).dt.strftime('%H:%M:%S').tolist() 
        first_time_point = pd.to_datetime(formatted_timepoints[0], format='%H:%M:%S')
        timepoints_in_seconds = [(pd.to_datetime(time, format='%H:%M:%S') - first_time_point).total_seconds() for time in formatted_timepoints]

        return timepoints_in_seconds, first_timestamp, rmod_column_name, second_column_name

    def filter_dataframe(self, df, rmod_filter, rmod_column_name):
        return df[df[rmod_column_name].astype(str).apply(lambda x: any(rmod in x for rmod in rmod_filter))]
    
    def get_antenna_filter_for_rmod(self, rmod, mapping_dict): # Returns the antenna filter list for a given rmod
        for key in mapping_dict:
            if key in rmod:
                return mapping_dict[key]
        return None

    def plot_rmod(self, rmod_df, time_datapoints, rmod_column_name, second_column_name, name, fig, first_timestamps, filename, filenames_in_order, color_start_index, max_time_value):
        colors = ['red', 'blue', 'green', 'purple', 'orange', 'pink', 'brown', 'gray', 'navy','darkgreen', 'maroon', 'darkorange', 'indigo', 'chocolate', 'deeppink', 'dimgray']
        line_styles = ['longdash', 'longdashdot', 'dot', 'dash', 'solid', 'dashdot']
        
        # Make configuration for each name value inside a config dictionary
        config = {
            'VSWR': {'title': 'VSWR by Time', 'yaxis_title': 'VSWR'},
            'RTWP': {'title': 'RTWP by Time', 'yaxis_title': 'RTWP (dBm)', 'yaxis_range': [-110, -50], 'yaxis_dtick': 5},
            'RSSI': {'title': 'RSSI by Time', 'yaxis_title': 'RSSI (dBm)', 'yaxis_range': [-110, 5], 'yaxis_dtick': 5},
            'ETP': {'title': 'ETP by Time', 'yaxis_title': 'ETP (W)', 'yaxis_range': [0, 30], 'yaxis_dtick': 1},
        }

        # Method for creating the graph lines for the ticks
        def create_grid_for_ticks(major_ticks, minor_ticks, orientation='vertical'):
            if orientation == 'vertical':
                y0, y1, xref, yref = 0, 1, None, 'paper'
            else:  # orientation is horizontal
                x0, x1, xref, yref = 0, 1, 'paper', None
                
            major_shapes = [{
                'type': 'line', 
                'x0': tick if orientation == 'vertical' else x0,
                'x1': tick if orientation == 'vertical' else x1,
                'y0': tick if orientation == 'horizontal' else y0,
                'y1': tick if orientation == 'horizontal' else y1,
                'xref': xref,
                'yref': yref,
                'line': {'color': 'lightgrey', 'width': 1.5},
            } for tick in major_ticks]
            
            minor_shapes = [{
                'type': 'line',
                'x0': tick if orientation == 'vertical' else x0,
                'x1': tick if orientation == 'vertical' else x1,
                'y0': tick if orientation == 'horizontal' else y0,
                'y1': tick if orientation == 'horizontal' else y1,
                'xref': xref,
                'yref': yref,
                'line': {'color': 'white', 'width': 0.5},
            } for tick in minor_ticks]
            
            return major_shapes + minor_shapes


        # Loop thru the rows in the dataframe for the given rmod
        for idx, row in rmod_df.iterrows():
            # Get the rmod_value and second_row_value for creating the legend
            rmod_value = row[rmod_column_name].split('/')[0]
            second_row_value = row[second_column_name]

            # Get the color and line_style
            color_idx = (idx + color_start_index) % len(colors)
            line_style_idx = int(re.findall("\d+", second_row_value)[0]) % len(line_styles)

            # Use different legen label formation for different dataframes
            if name in ['VSWR', 'RTWP', 'RSSI']:
                band_value = row.get('Supported TX bands') if name == 'VSWR' else row['RX carrier']
                # Convert y_values for to numbers if they are not already, also convert '-' values to nan values
                y_values = [float(value.replace(',', '.')) if isinstance(value, str) and value != '-' else value if value != '-' else np.nan for value in row.values[3:]]
                label_text = f"{filename} - {rmod_value} - {second_row_value} - {band_value}"
            else:
                # Convert mW values to W and to numbers and convert '-' values to nan values
                y_values = [float(value)/1000 if value != '-' else np.nan for value in row.values[2:]]
                label_text = f"{filename} - {rmod_value} - {second_row_value}"
            
            
            # Draw the datapoints for the given row
            fig.add_trace(go.Scatter(x=time_datapoints, y=y_values, mode='lines', name=label_text,
                                    line=dict(color=colors[color_idx], dash=line_styles[line_style_idx]),
                                    hovertemplate='%{fullData.name}: %{y}<extra></extra>'))

        # Make the title_prefix for the file
        title_prefix = ' <span style="color: #FF0000;">|</span> '.join([f"{filename}, {date}" for filename, date in zip(filenames_in_order, first_timestamps)])
        
        # Make the major minute ticks and minor 10 second ticks
        max_time_value = int(max_time_value)
        major_ticks = list(range(0, max_time_value+1, 60))
        minor_ticks = list(range(0, max_time_value+1, 10))
        all_ticks = sorted(set(major_ticks))
        ticktext = [f'{int(val/60)} min' if val in major_ticks else '' for val in all_ticks]

        if name in ["RTWP", "RSSI"]:
            y_major_ticks = list(range(config[name]['yaxis_range'][0], config[name]['yaxis_range'][1] + 1, 5))
            y_minor_ticks = list(range(config[name]['yaxis_range'][0], config[name]['yaxis_range'][1] + 1, 1))
            y_grid_shapes = create_grid_for_ticks(y_major_ticks, y_minor_ticks, orientation='horizontal')
        else:
            y_grid_shapes = []

        # Create grid shapes in line with the tickmarks on the x axis
        x_grid_shapes = create_grid_for_ticks(major_ticks, minor_ticks)
        # Combine the x and y axis shapes
        grid_shapes = x_grid_shapes + y_grid_shapes


        # Update figure layout according to the dataframe
        fig.update_layout(
            title=f'{title_prefix} {config[name]["title"]}',
            xaxis_title='Time (minutes)',
            yaxis_title=config[name]['yaxis_title'],
            yaxis=dict(range=config[name].get('yaxis_range'), dtick=config[name].get('yaxis_dtick')),
            xaxis=dict(tickvals=all_ticks, ticktext=ticktext, ticks='outside', tickwidth=2, ticklen=10, showgrid=False),
            shapes=grid_shapes, showlegend=True
        )
                    

def main():
    reader = DataReader(DATAFRAMES)

if __name__=="__main__":
    main()