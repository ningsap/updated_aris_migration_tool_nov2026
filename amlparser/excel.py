import openpyxl
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Font, Alignment
import html
from datetime import datetime
import os
import pytz


class Excel():


    def create(report_name, report_data, save_directory='output', timezone='local', wrap_text=False, max_column_width=100):
        """
        Outputs given data as excel file.
        Requires report data as dict.
    
    
        Parameters
        ----------
        report_name : string
            naming of the xls file
        report_data : list of dictionaries
            report content
        save_directory : string, optional
            directory name where the report will be saved. The default is 'output'.
        timezone: string, optional
            If set to "local", it will take the local time.
            Other valid values can be found under "TZ Database Name":  https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
            Example: "Asia/Manila"
        wrap_text : bool, optional
            Whether to wrap text in each cell. Default is False.
        max_column_width : int, optional
            Maximum column width. Default is 100.
    
        Returns
        -------
        file_path : string
    
        """
    
        #logger.info("Creating Report...")
    
        wb = Workbook()
        report = wb.active
        report.title = 'Report'
    
        # Styles
        fill_titles = PatternFill("solid", fgColor="0474c4")
        font_titles = Font(color="FFFFFF", bold=True, size=12)
        alignment_titles = Alignment(horizontal='center', vertical='center')
        fill_titles_dark = PatternFill("solid", fgColor="035c9c")

    
        # Insert all column titles
        columns = list(report_data[0].keys())
        for i, column_title in enumerate(columns, start=1):
            cell = report.cell(column=i, row=1)
            cell.font = font_titles
            if column_title in ['Path', 'Model Id', 'Model Name', 'Element Id', 'Stencil']:
                cell.fill = fill_titles_dark
            else:
                cell.fill = fill_titles
            cell.value = column_title
            cell.alignment = alignment_titles  # Center alignment
            column_letter = get_column_letter(i)
            column_width = max(len(column_title), max(len(str(row.get(column_title, ''))) for row in report_data)) + 2
            column_width = min(column_width, max_column_width)  
            report.column_dimensions[column_letter].width = column_width
    
        # Add filters to the column headers
        report.auto_filter.ref = report.dimensions
    
        # Insert report data
        for row_index, report_row in enumerate(report_data, start=2):
            for col_index, report_value in enumerate(report_row.values(), start=1):
                if isinstance(report_value, list):
                    report_value = ', '.join(report_value)  # Convert list to comma-separated string
                report_value = str(report_value)  # Convert value to string
                cell = report.cell(column=col_index, row=row_index, value=report_value)
                cell.alignment = Alignment(vertical='top')
                
                if ';' in report_value:
                    lines = report_value.split(';')
                    max_line_width = max(len(line) for line in lines)
                    if wrap_text:
                        cell.alignment = Alignment(vertical='top', wrap_text=True)
                    #cell.value = report_value.replace('\n', '\r\n')  # Replace '\n' with '\r\n' for proper line break rendering
                    if max_line_width > column_width - 2:
                        column_width = max_line_width + 2
                        column_width = min(column_width, max_column_width)  
                        report.column_dimensions[column_letter].width = column_width
                        
                # Check if the value starts with 'https' and add the "hyperlink" style
                if report_value.startswith('https'):
                    cell.hyperlink = report_value
                    cell.style = 'Hyperlink'

    
        # Apply light blue color to every second row
        for row in report.iter_rows(min_row=2):
            if row[0].row % 2 == 0:
                for cell in row:
                    cell.fill = PatternFill(start_color="E6F3F7", end_color="E6F3F7", fill_type="solid")
    
        # Make column header fixed (sticky)
        report.freeze_panes = "A2"
    
        # Increase header height by 100%
        report.row_dimensions[1].height = 30
    
        # Center align the header row
        for cell in report[1]:
            cell.alignment = alignment_titles
    
        # Configure File Naming
        output_file_name = report_name + '_' + datetime.now().strftime('%Y.%m.%d_%H.%M.%S') + '.xlsx'
        if timezone != 'local':
            tz = pytz.timezone(timezone)
            output_file_name = report_name + '_' + datetime.now(tz).strftime('%Y.%m.%d_%H.%M.%S') + '.xlsx'
    
        # Save File
        if not os.path.exists(save_directory):
            os.makedirs(save_directory, exist_ok=True)
    
        file_path = os.path.join(save_directory, output_file_name)
        wb.save(file_path)
        wb.close()
    
        #logger.info('Report exported: ' + file_path)
    
        return file_path
    
    
    def create_with_sheets(report_name, report_data_dict, save_directory='output', timezone='local', wrap_text=False, max_column_width=100):
        """
        Outputs given data as an Excel file with multiple sheets.
    
        Parameters
        ----------
        report_name : str
            Name of the Excel file.
        report_data_dict : dict
            A dictionary where keys are sheet names and values are lists of dictionaries representing data for each sheet.
        save_directory : str, optional
            Directory where the report will be saved. Default is 'output'.
        timezone: str, optional
            If set to "local", it will take the local time. Other valid values can be found under "TZ Database Name":
            Example: "Asia/Manila"
        wrap_text : bool, optional
            Whether to wrap text in each cell. Default is False.
        max_column_width : int, optional
            Maximum column width. Default is 100.
    
        Returns
        -------
        file_path : str
            The path to the generated Excel file.
        """
    
        wb = Workbook()
    
        for sheet_name, report_data in report_data_dict.items():
            report = wb.create_sheet(title=sheet_name)
    
            # Styles
            fill_titles = PatternFill("solid", fgColor="0474c4")
            font_titles = Font(color="FFFFFF", bold=True, size=12)
            alignment_titles = Alignment(horizontal='center', vertical='center')
    
            if report_data:
                # Insert all column titles
                columns = list(report_data[0].keys())
                for i, column_title in enumerate(columns, start=1):
                    cell = report.cell(column=i, row=1)
                    cell.font = font_titles
                    cell.fill = fill_titles
                    cell.value = column_title
                    cell.alignment = alignment_titles  # Center alignment
                    column_letter = get_column_letter(i)
                    column_width = max(len(column_title), max(len(str(row.get(column_title, ''))) for row in report_data)) + 2
                    column_width = min(column_width, max_column_width)
                    report.column_dimensions[column_letter].width = column_width
    
                # Add filters to the column headers
                report.auto_filter.ref = report.dimensions
    
                # Insert report data
                for row_index, report_row in enumerate(report_data, start=2):
                    for col_index, column_title in enumerate(columns, start=1):
                        report_value = report_row.get(column_title)
                        if str(report_value) in [None, 'nan']:
                            report_value = ""  # Handle None values
                        #if str(report_value).endswith('.0'):
                        #    report_value = int(str(report_value)[:-2])
                        elif isinstance(report_value, list):
                            report_value = ', '.join(map(str, report_value))  # Convert list to comma-separated string
                        else:
                            report_value = str(report_value)  # Convert value to string
                        cell = report.cell(column=col_index, row=row_index, value=report_value)
                        cell.alignment = Alignment(vertical='top')
                        if wrap_text:
                            cell.alignment = Alignment(vertical='top', wrap_text=True)
                            if len(report_value) > column_width - 2:
                                wrapped_width = max(len(line) for line in report_value.split("\n"))
                                column_width = max(column_width, wrapped_width) + 2
                                column_width = min(column_width, max_column_width)
                                report.column_dimensions[column_letter].width = column_width
    
                # Apply light blue color to every second row
                for row in report.iter_rows(min_row=2):
                    if row[0].row % 2 == 0:
                        for cell in row:
                            cell.fill = PatternFill(start_color="E6F3F7", end_color="E6F3F7", fill_type="solid")
    
                # Make column header fixed (sticky)
                report.freeze_panes = "A2"
    
                # Increase header height by 100%
                report.row_dimensions[1].height = 30
    
                # Center align the header row
                for cell in report[1]:
                    cell.alignment = alignment_titles
    
        # Remove the default sheet created by openpyxl
        wb.remove(wb.active)
    
        # Configure File Naming
        output_file_name = report_name + '_' + datetime.now().strftime('%Y.%m.%d_%H.%M.%S') + '.xlsx'
        if timezone != 'local':
            tz = pytz.timezone(timezone)
            output_file_name = report_name + '_' + datetime.now(tz).strftime('%Y.%m.%d_%H.%M.%S') + '.xlsx'
    
        # Save File
        if not os.path.exists(save_directory):
            os.makedirs(save_directory, exist_ok=True)
    
        file_path = os.path.join(save_directory, output_file_name)
        wb.save(file_path)
    
        return file_path
    
    
    def create_from_template(report_name, report_data, template_name, worksheet_name, save_directory='output',
                                          publishedRevision=False, timezone='local'):
        """
        Outputs given data as excel file.
        Requires report data as list of lists and excel template in root directory
    
        Parameters
        ----------
        report_name : string
            naming of the xls file
        report_data : list of lists
            report content
        template_name : string
        worksheet_name : string
        save_directory : string, optional
            directory name where the report will be saved. The default is 'output'.
        publishedRevision : boolean, optional
            Will be included in the naming of the xls file. The default is False.
        timezone: string, optional
            If set to "local", it will take the local time.
            Other valid values can be found under "TZ Database Name":  https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
            Example: "Asia/Manila"
    
    
        Returns
        -------
        file_path : string
    
        """
    
        #logger.info("Create Excel File ")
        wb = openpyxl.load_workbook(template_name)
    
        # Create Excel Report Worksheet Process Information
        ws = wb[worksheet_name]
    
        row_num = 1
    
        for row in report_data:
    
            row_num += 1
            col_num = 1
    
            for col in row:
                try:
                    ws.cell(row=row_num, column=col_num).value = html.unescape(str(col))
                    ws.cell(row=row_num, column=col_num).font = Font(size=8)
                    col_num += 1
                except:
                    pass
                    #logger.warning('Couldnt print' + str(col_num) + str(row_num) + str(col))
    
        if publishedRevision == False:
            revision = 'Unpublished'
        else:
            revision = 'Published'
    
        # Configure File Naming
        output_file_name = report_name + ' ' + str(revision) + ' %Y.%m.%d_%H.%M.%S' + '.xlsx'
        filename = datetime.now().strftime(output_file_name)
        if timezone != 'local':
            tz = pytz.timezone(timezone)
            filename = datetime.now(tz).strftime(output_file_name)
    
        # Save File
        if not os.path.exists(save_directory):
            os.makedirs(save_directory, exist_ok=True)
    
        file_path = os.path.join(save_directory, filename)
        wb.save(file_path)
        wb.close()
    
        #logger.info('Report created: ' + file_path)
    
        return file_path
    

    def create_v2(report_name, report_data, save_directory='output', timezone='local', wrap_text=False, max_column_width=100, special_color_attributes=None):
        """
        Outputs given data as excel file.
        Requires report data as dict.
        
        Parameters
        ----------
        report_name : string
            naming of the xls file
        report_data : list of dictionaries
            report content
        save_directory : string, optional
            directory name where the report will be saved. The default is 'output'.
        timezone: string, optional
            If set to "local", it will take the local time.
            Other valid values can be found under "TZ Database Name":  https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
            Example: "Asia/Manila"
        wrap_text : bool, optional
            Whether to wrap text in each cell. Default is False.
        max_column_width : int, optional
            Maximum column width. Default is 100.
        special_color_attributes : list, optional
            List of column names that should be highlighted and placed at the front of the table. Default is None.
        
        Returns
        -------
        file_path : string
        
        """
    
        wb = Workbook()
        report = wb.active
        report.title = 'Report'
        
        # Styles
        fill_titles = PatternFill("solid", fgColor="0474c4")
        font_titles = Font(color="FFFFFF", bold=True, size=12)
        alignment_titles = Alignment(horizontal='center', vertical='center')
        fill_titles_dark = PatternFill("solid", fgColor="035c9c")
    
        if special_color_attributes is None:
            special_color_attributes = []
    
        # Get the keys in the order they appear in the first dictionary
        primary_columns = list(report_data[0].keys())
    
        # Collect all unique keys from all dictionaries in report_data
        all_keys = set()
        for row in report_data:
            all_keys.update(row.keys())
    
        # Filter special attributes to keep the order and include only those present in the data
        special_columns = [attr for attr in special_color_attributes if attr in all_keys]
        
        # Order primary columns, starting with special columns
        remaining_columns = [col for col in primary_columns if col not in special_columns]
        
        # Append any additional keys found in other dictionaries that weren't in the first dictionary
        additional_columns = [key for key in all_keys if key not in special_columns and key not in primary_columns]
        
        # Combine special, primary, and additional columns
        columns = special_columns + remaining_columns + additional_columns
    
        # Insert all column titles
        for i, column_title in enumerate(columns, start=1):
            cell = report.cell(column=i, row=1)
            cell.font = font_titles
            if column_title in special_columns:
                cell.fill = fill_titles_dark
            else:
                cell.fill = fill_titles
            cell.value = column_title
            cell.alignment = alignment_titles  # Center alignment
            column_letter = get_column_letter(i)
            column_width = max(len(column_title), max(len(str(row.get(column_title, ''))) for row in report_data)) + 2
            column_width = min(column_width, max_column_width)  
            report.column_dimensions[column_letter].width = column_width
    
        # Add filters to the column headers
        report.auto_filter.ref = report.dimensions
    
        # Insert report data
        for row_index, report_row in enumerate(report_data, start=2):
            for col_index, column_title in enumerate(columns, start=1):
                report_value = report_row.get(column_title, '')
                if isinstance(report_value, list):
                    report_value = ', '.join(report_value)  # Convert list to comma-separated string
                report_value = str(report_value)  # Convert value to string
                cell = report.cell(column=col_index, row=row_index, value=report_value)
                cell.alignment = Alignment(vertical='top')
                
                if ';' in report_value:
                    lines = report_value.split(';')
                    max_line_width = max(len(line) for line in lines)
                    if wrap_text:
                        cell.alignment = Alignment(vertical='top', wrap_text=True)
                    if max_line_width > column_width - 2:
                        column_width = max_line_width + 2
                        column_width = min(column_width, max_column_width)  
                        report.column_dimensions[column_letter].width = column_width
                        
                # Check if the value starts with 'https' and add the "hyperlink" style
                if report_value.startswith('https'):
                    cell.hyperlink = report_value
                    cell.style = 'Hyperlink'
    
        # Apply light blue color to every second row
        for row in report.iter_rows(min_row=2):
            if row[0].row % 2 == 0:
                for cell in row:
                    cell.fill = PatternFill(start_color="E6F3F7", end_color="E6F3F7", fill_type="solid")
    
        # Make column header fixed (sticky)
        report.freeze_panes = "A2"
    
        # Increase header height by 100%
        report.row_dimensions[1].height = 30
    
        # Center align the header row
        for cell in report[1]:
            cell.alignment = alignment_titles
    
        # Configure File Naming
        output_file_name = report_name + '_' + datetime.now().strftime('%Y.%m.%d_%H.%M.%S') + '.xlsx'
        if timezone != 'local':
            tz = pytz.timezone(timezone)
            output_file_name = report_name + '_' + datetime.now(tz).strftime('%Y.%m.%d_%H.%M.%S') + '.xlsx'
    
        # Save File
        if not os.path.exists(save_directory):
            os.makedirs(save_directory, exist_ok=True)
    
        file_path = os.path.join(save_directory, output_file_name)
        wb.save(file_path)
        wb.close()
    
        return file_path
