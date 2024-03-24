from datetime import datetime, timedelta

def convert_to_long_format(date_str):
    # Convert the string to a datetime object
    date_obj = datetime.strptime(date_str, "%Y%m%d")
    
    # Convert the datetime object to the desired format
    long_format_date = date_obj.strftime("%d %B, %Y")  # %d for day, %B for full month name, %Y for year
    return long_format_date

def date_range(start_date, end_date):
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    dates = []
    while start <= end:
        dates.append(start.strftime("%Y%m%d"))
        start += timedelta(days=1)
    return dates