# -*- coding: utf-8 -*-
"""
Created on Thu Jul 16 10:57:08 2026

@author: CHall
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import holidays
from datetime import datetime
import streamlit as st
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    KeepTogether,
    PageBreak
)
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


#%%define analysis function
def analysis(
    df,
    clinic_name,
    department_fte,
    exam_room_count,
    growth_rate,
    open_time,
    close_time,
    turnover_time,
    appointments_to_exclude
):
    us_holidays = holidays.US()
    optimal_capacity = 0.85 * exam_room_count
    
    
    #cancellation analysis
    countcancelled = df["Appointment Status"].str.contains("Can", case=False, na=False).sum()
    countnoshow = df["Appointment Status"].str.contains("No Show", case=False, na=False).sum()
    countcompleted = df["Appointment Status"].str.contains("Comp", case=False, na=False).sum()
    numappointments = len(df)
    percentcancelled = (countcancelled/numappointments) * 100
    percentnoshow = (countnoshow/numappointments) * 100
    percentcompleted = (countcompleted/numappointments) * 100
    count_noappear = countcancelled+countnoshow
    percent_noappear = (count_noappear / numappointments) * 100
    
    # =============================================================================
    # NO SHOW / CANCELLATION TABLE
    # =============================================================================
    
    no_show_table_data = [
        ["Category", "Count", "Percent"],
        ["Cancelled Appointments", f"{countcancelled:0.0f}", f"{percentcancelled:0.2f}%"],
        ["No-Show Appointments", f"{countnoshow:0.0f}", f"{percentnoshow:0.2f}%"],
        ["Completed Appointments", f"{countcompleted:0.0f}", f"{percentcompleted:0.2f}%"],
        ["Total Appointments", f"{numappointments}", "--"]
    ]
    
    # add appointment date/get ride of weekends
    df["Appointment Date"] = pd.to_datetime(
    df["Appointment Date"],
    errors="coerce"
)
    bad_dates = df["Appointment Date"].isna().sum()

    if bad_dates > 0:
        st.warning(f"{bad_dates} appointments have invalid dates")
    df = df[df["Appointment Date"].dt.dayofweek < 5]
    df["Date"] = pd.to_datetime(df["Appointment Date"]).dt.date
    
    start_date = df["Appointment Date"].min()
    end_date = df["Appointment Date"].max()
    
    weeks_in_data = (end_date - start_date).days / 7
    
    
    #exclude cancelations and no shows from df
    exclude_keywords = ['can', 'no show' ]
    
    mask = df["Appointment Status"].str.contains(
        "|".join(exclude_keywords),
        case=False,
        na=False
    )
    df = df[~mask]
    
    
    # provider analysis 
    provider_results = []
    for name, info in department_fte.items():

        data = df[df["Department"].str.contains(name, na=False)]
    
        patient_time = data["Appointment Length"].sum()
        turnover_total = len(data) * turnover_time
    
        total_patient_time = (patient_time + turnover_total)/60
    
        FTE = info["fte"]
    
        appt_length = data["Appointment Length"].mean()
        num_appoint = len(data)
    
        appt_length_turnover = (appt_length + turnover_time) / 60
    
        provider_hours = FTE * 40 * weeks_in_data
    
        provider_capacity = provider_hours / appt_length_turnover
    
        provider_capacity_percent = (
            num_appoint / provider_capacity
        ) * 100
    
        provider_results.append([
            info["name"],
            FTE,
            f"{appt_length:.0f} mins",
            f"{provider_capacity:0.0f}",
            num_appoint,   
            f"{provider_capacity_percent:0.0f}%"
        ])
    
    
    
    #exclude procedures, telehealth, visits from df
    exclude_keywords = appointments_to_exclude
    
    if appointments_to_exclude:
    
     mask = df["Visit Type"].str.contains(
         "|".join(appointments_to_exclude),
         case=False,
         na=False
     )
    
     df = df[~mask]
    
    
    #add day of week to df for each appointment
    df["Day of Week"] = df["Appointment Date"].dt.day_name()
    
    #count # of appointments per date
    appointments_by_weekday = df.groupby("Day of Week").size()
    
    
    
    #Number each day with appointment
    
    df["Day of Week"] = pd.to_datetime(df["Appointment Date"]).dt.day_name()
    
    days_per_weekday = (
        df.groupby("Day of Week")["Date"]
        .nunique()
    )
    
    
    
    #calculate average number of appointments per day
    avgperday = appointments_by_weekday / days_per_weekday
    avgperday = np.ceil(avgperday)
    
    # =============================================================================
    # FORMAT AVERAGE APPOINTMENTS PER WEEKDAY TABLE
    # =============================================================================
    
    # Ensure correct weekday order
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    avgperday = avgperday.reindex(weekday_order)
    
    # Build table data
    weekday_table_data = [
        ["Day of Week", "Avg Appointments per Day"]
    ]
    
    for day, value in avgperday.items():
        weekday_table_data.append([day, value])
        
    busiestday = str(avgperday.idxmax())
    

        
    #establish time bounds of each appointment
    # Date range in your dataset
    start_date = df["Appointment Date"].min().date()
    end_date = df["Appointment Date"].max().date()
    
    # Create every day in range
    all_days = pd.date_range(
        start=start_date,
        end=end_date,
        freq="D"
    )
    
    # Keep weekdays and remove holidays
    clinic_days = [
        day for day in all_days
        if day.weekday() < 5 and day.date() not in us_holidays
    ]
    
    numberofdaysindf = len(clinic_days)
    
    # Hours open per day
    hours_per_day = (
        pd.Timestamp(close_time) - pd.Timestamp(open_time)
    ).seconds / 3600
    
    df["start"] = pd.to_datetime(df["Appointment Date"])
    df["end"] = df["start"] + pd.to_timedelta(df["Appointment Length"]+turnover_time, unit="m")
    
    
    start_date = df["Appointment Date"].min().date()
    end_date = df["Appointment Date"].max().date()
    
    all_days = pd.date_range(
        start=start_date,
        end=end_date,
        freq="D"
    )

    full_time_index = pd.DatetimeIndex([])
    
    for day in clinic_days:
        day_start = pd.Timestamp(day.date()) + pd.Timedelta(open_time)
        day_end = pd.Timestamp(day.date()) + pd.Timedelta(close_time)
    
        day_minutes = pd.date_range(
            start=day_start,
            end=day_end,
            freq="1min"
        )
    
        full_time_index = full_time_index.append(day_minutes)
        
        events = []
    
    for _, row in df.iterrows():
        events.append((row["start"], +1))
        events.append((row["end"], -1))
    
    events = sorted(events)
    
    event_df = pd.DataFrame(
        events,
        columns=["time", "change"]
    )
    
    # Combine events happening at the same time
    event_df = (
        event_df
        .groupby("time")["change"]
        .sum()
    )
    
    # Calculate running room occupancy
    occupancy_events = event_df.cumsum()
    
    occupancy_series = (
        occupancy_events
        .reindex(full_time_index, method="ffill")
        .fillna(0)
    )
    
    
    avg_by_time = occupancy_series.groupby(occupancy_series.index.time).mean()
  
    # analyze exam room occupation
    countover = 0
    countunder = 0
    countmax = 0
    for value in occupancy_series:
        if value>=21:
            countover = countover + 1
    for value in occupancy_series:
        if value<21:
            countunder = countunder + 1
    for value in occupancy_series:
        if value>=exam_room_count:
            countmax = countmax+1
            
    countmax = countmax/60
    countover = countover / 60
    countunder = countunder/60
            
    room_results = []  
    max_capacity_percent = ((countmax)/(len(occupancy_series)/60))*100
    #print(f'{countmax} hours of max capacity ({exam_room_count} rooms), {max_capacity_percent:0.2f}% of {open_hours:0.1f} open hours.')
    
    over_capacity_hours = (countover/(len(occupancy_series)/60))
    percent_overcapacity = (countover/(len(occupancy_series)/60)) * 100
    percent_undercapacity = (countunder/(len(occupancy_series)/60)) * 100
    
    numappointments = len(df)
    roomtimeavailable = exam_room_count * (len(occupancy_series)/60)
    totalappointmenttime = df["Appointment Length"].sum()/60
    totalturnovertime = numappointments * (turnover_time/60)
    totalrequiredroomtime = totalappointmenttime + totalturnovertime
    
    examroompercentcapacity = (totalrequiredroomtime / roomtimeavailable) * 100
    
    
    room_results.append([
        f"Maximum Room Capacity ({exam_room_count} rooms)",
        f"{countmax:0.2f} hours",
        f"{max_capacity_percent:0.2f}% of open hours"
    ])
    
    room_results.append([
        f"Room Utilization ≥85% ({optimal_capacity} or more rooms)",
        f"{countover:0.2f} hours",
        f"{percent_overcapacity:0.2f}% of open hours"
    ])
    
    room_results.append([
        f"Room Utilization <85% (less than {optimal_capacity} rooms)",
        f"{countunder:0.2f} hours",
        f"{percent_undercapacity:0.2f}% of open hours"
    ])
    
    room_results.append([
        "Total Clinic Open Time",
        f"{len(occupancy_series)/60:0.2f} hours",
        "--"
    ])
    
    busiest_occupancy = occupancy_series[
        occupancy_series.index.day_name() == busiestday
    ]
    
    wednesday = occupancy_series[
        occupancy_series.index.day_name() == busiestday
    ].copy()
    
    # group by time of day
    average_busiest_day = (
        busiest_occupancy
        .groupby(busiest_occupancy.index.time)
        .mean()
    )
    
    # Convert datetime.time index to minutes
    time_minutes = [
        t.hour * 60 + t.minute 
        for t in average_busiest_day.index
    ]
    
    plt.figure(figsize=(12,5))
    
    plt.plot(
        time_minutes,
        average_busiest_day.values
    )
    
    plt.xlabel("Time of Day")
    plt.ylabel("Exam Rooms Occupied Simulataneously")
    plt.title(f"Average Clinic Occupancy on {busiestday}")
    
    # Convert x-axis back to hours for readability
    plt.xticks(
        range(480, 1021, 60),
        [f"{h}:00" for h in range(8, 18)]
    )
    plt.grid(True)
    
    plt.axhline(
        exam_room_count,
        linestyle="--",
        label="Maximum Capacity",
        color = 'Red'
    )
    
    plt.axhline(
        optimal_capacity,
        linestyle="--",
        label="Optimal Capacity",
        color = 'Orange'
    )
    plt.legend()
    plt.tight_layout()
    
    plt.savefig(
        "clinic_occupancy_busiest_day.png",
        dpi=300,
        bbox_inches="tight"
    )
    
    plt.close()
    
    #looking forward calculations
    years = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    
    # Average appointment length in minutes
    average_appointment_length = df["Appointment Length"].mean()
    
    future_capacity = {}
    
    year_85_percent = None
    
    for year in years:
        # need to annualize number of appointments so it is year by year
        years_of_data = max((end_date - start_date).days/365.25, 1/365.25)
        
        annualized_appointments = ( # num. of appointments per year based off of data
            numappointments/years_of_data
        )
        
        annualized_room_hours = (roomtimeavailable/years_of_data)
            
        
        # Grow number of appointments
        future_appointments = annualized_appointments * (1 + growth_rate)**year #avg. num of appointments in coming years
        
        avg_visit_hours = (
            average_appointment_length + turnover_time
        ) / 60

        possible_appointments = (
            annualized_room_hours / avg_visit_hours
        )


        # Calculate utilization
        future_utilization = (
            future_appointments / possible_appointments
        ) * 100
        
        if year_85_percent is None and future_utilization >=85:
            year_85_percent = year
        
        future_capacity[year] = {
            "Appointments": future_appointments,
            "Possible Appointments": possible_appointments,
            "Utilization": future_utilization
        }
    
    future_capacity_table_data =  [["Future Year", "Projected Appointments", "Possible Appointments", "Room Utilization"]]

    
    
    for year, values in future_capacity.items():
        future_capacity_table_data.append([
            f"{year} years",
            f"{values['Appointments']:,.0f}",
            f"{values['Possible Appointments']:,.0f}",
            f"{values['Utilization']:,.1f}%"
        ])
        
    fig, ax = plt.subplots(figsize=(6, 6))
    
    labels = [
        "Completed",
        "Cancelled",
        "No Show"
    ]
    
    sizes = [
        countcompleted,
        countcancelled,
        countnoshow
    ]
    
    colors = [
        "#005B96",  # blue - completed
        "#7FC8E8",  # light blue - cancelled
        "#A6A6A6"   # gray - no show
    ]
    
    # Create pie chart without labels or percentages
    wedges, _ = ax.pie(
        sizes,
        colors=colors,
        startangle=90
    )
    
    # Add percentage labels outside the pie
    total = sum(sizes)
    
    for wedge, value in zip(wedges, sizes):
        angle = (wedge.theta2 + wedge.theta1) / 2
        
        x = np.cos(np.deg2rad(angle))
        y = np.sin(np.deg2rad(angle))
        
        percentage = value / total * 100
        
        ax.annotate(
            f"{percentage:.1f}%",
            xy=(x, y),
            xytext=(1.2*x, 1.1*y),
            ha="center",
            va="center",
            fontsize=11
        )
    
    # Legend with descriptions only
    ax.legend(
        wedges,
        labels,
        title="Appointment Status",
        loc="center left",
        bbox_to_anchor=(1, 0.5)
    )
    
    ax.set_title("Appointment Status Breakdown")
    
    plt.tight_layout()
    return {
        "no_show": no_show_table_data,
        "provider": provider_results,
        "rooms": room_results,
        "future": future_capacity_table_data,
        "weekday": weekday_table_data,
        "busiestday": busiestday,
        "roomtimeavailable": roomtimeavailable,
        "totalrequiredroomtime": totalrequiredroomtime,
        "examroompercentcapacity": examroompercentcapacity,
        "optimal_capacity": optimal_capacity,
        "appointment_chart": fig,    
        "data_start_date": start_date,
        "data_end_date": end_date,
            
        "open_time": open_time,
        "close_time": close_time,
        "growth_rate": growth_rate,
        "appointments_to_exclude": appointments_to_exclude,
        "average_appointment_length": average_appointment_length,
        "numberofdaysindf":numberofdaysindf,
        "year_85_percent":year_85_percent
    

    }

#%% PDF Function
def create_capacity_pdf(
    results,
    clinic_name,
    df,
    turnover_time,
    exam_room_count,
  #  optimal_capacity,
    output_path=None
):

    if output_path is None:
        output_path = f"{clinic_name}_Capacity_Report.pdf"


    # Pull results from analysis dictionary
    no_show_table_data = results["no_show"]
    provider_results = results["provider"]
    room_results = results["rooms"]
    future_capacity_table_data = results["future"]


    # Additional values stored from analysis
    roomtimeavailable = results["roomtimeavailable"]
    totalrequiredroomtime = results["totalrequiredroomtime"]
    examroompercentcapacity = results["examroompercentcapacity"]
    weekday_table_data = results["weekday"]
    busiestday = results["busiestday"]
    optimal_capacity = results["optimal_capacity"]
        
    open_time = results["open_time"]
    close_time = results["close_time"]
    growth_rate = results["growth_rate"]
    appointments_to_exclude = results["appointments_to_exclude"]
    numberofdaysindf = results["numberofdaysindf"],
    year_85_percent = results['year_85_percent']

    
    data_start_date = results["data_start_date"].strftime("%B %d, %Y")
    data_end_date = results["data_end_date"].strftime("%B %d, %Y")



    report_date = datetime.today().strftime("%B %d, %Y")
    report_time = datetime.today().strftime("%I:%M %p")

    styles = getSampleStyleSheet()

    centered_heading = ParagraphStyle(
        "CenteredHeading",
        parent=styles["Heading2"],
        alignment=TA_CENTER
    )

    note_style = ParagraphStyle(
        "NoteStyle",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10
    )

    centered_note_style = ParagraphStyle(
        "CenteredNoteStyle",
        parent=note_style,
        alignment=TA_CENTER
    )

    subtitle_style = ParagraphStyle(
        "SubtitleStyle",
        parent=styles["BodyText"],
        alignment=TA_CENTER,
        fontSize=10
    )

    pdf_file = f"{clinic_name}_Capacity_Report.pdf"

    doc = SimpleDocTemplate(
        f"{clinic_name}_Capacity_Report.pdf",
        pagesize=letter,
        topMargin=60
    )

    styles = getSampleStyleSheet()

    content = []


    # Title
    content.append(
        Paragraph(f"{clinic_name} Capacity Analysis", styles["Title"])
    )

    content.append(Spacer(1, 2))

    content.append(
        Paragraph(
            f"""
            REPORT GENERATED: {report_date} at {report_time}
            <br/>
            ANALYSIS DATES: {data_start_date} - {data_end_date}
            """,
            subtitle_style
        )
    )

    content.append(Spacer(1, 2))

    # Provider Summary
    provider_table_data = [
        [
            "Department",
            "FTE",
            "Avg. Appt. Length",
            "Provider Capacity",
            "Appointments Completed",
            "Capacity %"
        ]
    ] + provider_results

    provider_table = Table(
        provider_table_data,
        hAlign="CENTER"
    )

    provider_table_style = [
        ("GRID", (0,0), (-1,-1), 0.5, None),
        ("BACKGROUND", (0,0), (-1,0), "#d3d3d3"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "CENTER")
    ]
    # Conditional formatting for Percent Capacity column
    for row_index, row in enumerate(provider_results, start=1):
        percent = float(row[5].replace("%", ""))

        if percent < 75:
            provider_table_style.append(
                ("TEXTCOLOR", (5, row_index), (5, row_index), "green")
            )
        elif percent < 85:
            provider_table_style.append(
                ("TEXTCOLOR", (5, row_index), (5, row_index), "orange")
            )
        else:
            provider_table_style.append(
                ("TEXTCOLOR", (5, row_index), (5, row_index), "red")
            )


    provider_table.setStyle(TableStyle(provider_table_style))

    content.append(
        Paragraph("Provider Capacity Analysis", centered_heading)
    )

    content.append(Spacer(1,2))

    content.append(provider_table)
    content.append(Spacer(1, 2))
    
    open_dt = datetime.strptime(open_time, "%H:%M:%S")
    close_dt = datetime.strptime(close_time, "%H:%M:%S")
    
    hoursofbeingopen = (close_dt - open_dt).total_seconds() / 3600

    content.append(
        Paragraph(
            f"""
            Note: Provider capacity is calculated by dividing the actual number of appointments conducted by the maximum number of appointments providers can complete based on 4-week average FTE, average appointment length, and a {turnover_time} minute turnover time for every appointment. Turnover time is not applied to the average appointment lengths seen here.
            """,
            centered_note_style
        )
    )

    content.append(Spacer(1, 2))

    styles = getSampleStyleSheet()

    centered_heading = ParagraphStyle(
        "CenteredHeading",
        parent=styles["Heading2"],
        alignment=TA_CENTER
    )

    # Overall Exam Room Capacity Table

    overall_table_data = [
        ["Metric", "Available Room Hours", "Used Room Hours", "Utilization"],
        [
            "Overall Exam Room Utilization",
            f"{roomtimeavailable:0.0f} hours",
            f"{totalrequiredroomtime:0.0f} hours",
            f"{examroompercentcapacity:0.2f}%"
        ]
    ]

    overall_table = Table(
        overall_table_data,
        hAlign="CENTER"
    )

    overall_table_style = [
        ("GRID", (0,0), (-1,-1), 0.5, None),
        ("BACKGROUND", (0,0), (-1,0), "#d3d3d3"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("FONTNAME", (0,1), (-1,1), "Helvetica-Bold")
    ]

    # Color utilization percentage
    if examroompercentcapacity >= 85:
        utilization_color = "red"
    else:
        utilization_color = "green"

    overall_table_style.append(
        ("TEXTCOLOR", (3,1), (3,1), utilization_color)
    )

    overall_table.setStyle(TableStyle(overall_table_style))


    # Add table to PDF
    content.append(Spacer(1,2))

    content.append(
        Paragraph("Overall Exam Room Capacity", centered_heading)
    )

    content.append(Spacer(1,2))

    content.append(overall_table)

    content.append(
        Paragraph(
            f"""
            Note: Exam room capacity calculated by total hours used by 
            appointments with {turnover_time} minute turnover for each 
            appointment divided by the available exam room hours ({hoursofbeingopen} 
            hour days * {exam_room_count} exam rooms * number of open days.
                                                                                                                            )
            """,
            centered_note_style
        )
    )

    room_table_data = [
        ["Metric", "Total Hours", "Percentage"]
    ] + room_results


    room_table = Table(
        room_table_data,
        hAlign="CENTER"
    )

    room_table_style = [
        ("GRID", (0,0), (-1,-1), 0.5, None),
        ("BACKGROUND", (0,0), (-1,0), "#d3d3d3"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold")
    ]

    # Color only the overall utilization percentage
    overall_percent = examroompercentcapacity


    room_table_style.append(
        ("TEXTCOLOR", (2,3), (2,3), utilization_color)
    )

    room_table.setStyle(TableStyle(room_table_style))
    content.append(
        Paragraph("Exam Room: Utilization Analysis by Time", centered_heading)
    )

    content.append(Spacer(1,2))

    content.append(room_table)

    content.append(
        Paragraph(
            f"""
            Note: Exam room utilization by time was determined by adding a 
            {turnover_time} minute turnover to each appointment slot, 
            and counting the number of exam rooms that are occupied simulatenously 
            for every minute the clinic has been open from {data_start_date} until 
            {data_end_date}
            """,
            centered_note_style
        )
    )

    no_show_table = Table(no_show_table_data, hAlign="CENTER")

    last_row = len(no_show_table_data) - 1

    no_show_table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, None),
        ("BACKGROUND", (0,0), (-1,0), "#d3d3d3"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),

        # Bold last row
        ("FONTNAME", (0,last_row), (-1,last_row), "Helvetica-Bold"),
    ]))



    content.append(
        KeepTogether([
            Paragraph("Appointment Outcomes", centered_heading),
            Spacer(1, 5),
            no_show_table,
            Spacer(1, 5),
            Paragraph(
                """
                Note: Cancelled and no-show appointments were not 
                included in clinic space or provider capacities.
                """,
                centered_note_style
            )
        ])
    )

    weekday_table = Table(
        weekday_table_data,
        hAlign="CENTER"
    )


    # Find row with highest average appointments
    max_avg_row = max(
        range(1, len(weekday_table_data)),  # skip header row
        key=lambda i: weekday_table_data[i][1]
    )


    weekday_table_style = [
        ("GRID", (0,0), (-1,-1), 0.5, None),
        ("BACKGROUND", (0,0), (-1,0), "#d3d3d3"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("BACKGROUND", (0, max_avg_row), (-1, max_avg_row), "#D3F9D8"),
        ("FONTNAME", (0, max_avg_row), (-1, max_avg_row), "Helvetica-Bold"),
    ]

    weekday_table.setStyle(TableStyle(weekday_table_style))



    content.append(
        Paragraph("Average Appointments per Day of Week", centered_heading)
    )


    content.append(Spacer(1, 5))

    content.append(weekday_table)

    content.append(
        Paragraph(
            f"""
            Note: Average appointments per day are calculated by 
            dividing the total number of appointments
            for each weekday by the number of occurrences 
            of that weekday in the dataset. The day with the highest 
            average is highlighted green.
            """,
            centered_note_style
        )
    )

    content.append(Spacer(1, 5))

    content.append(
        Paragraph(
            f"Average Clinic Occupancy on the Busiest Day of the Week",
            centered_heading
        )
    )

    content.append(Spacer(1, 10))

    occupancy_img = Image(
        "clinic_occupancy_busiest_day.png",
        width=450,
        height=225
    )

    # Put image inside a bordered box
    occupancy_box = Table(
        [[occupancy_img]],
        hAlign="CENTER"
    )

    occupancy_box.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 1, None),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
        ("TOPPADDING", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))

    content.append(occupancy_box)


    content.append(
        Paragraph(
            f"""
            Note: Average number of exam rooms occupied each hour on 
            {busiestday}, the busiest day each week.
            """,
            centered_note_style
        )
    )

    future_capacity_table = Table(
        future_capacity_table_data,
        hAlign="CENTER"
    )

    future_capacity_table_style = [
        ("GRID", (0,0), (-1,-1), 0.5, None),
        
        # Header formatting
        ("BACKGROUND", (0,0), (-1,0), "#d3d3d3"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        
        # Center numbers
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
    ]

    # Highlight years where utilization exceeds capacity
    for row_index, row in enumerate(future_capacity_table_data[1:], start=1):
        utilization = float(row[3].replace("%",""))
        
        if utilization >= 100:
            future_capacity_table_style.append(
                ("TEXTCOLOR", (3,row_index), (3,row_index), "red")
            )
        elif utilization >= 85:
            future_capacity_table_style.append(
                ("TEXTCOLOR", (3,row_index), (3,row_index), "orange")
            )
        else:
            future_capacity_table_style.append(
                ("TEXTCOLOR", (3,row_index), (3,row_index), "green")
            )

    future_capacity_table.setStyle(
        TableStyle(future_capacity_table_style)
    )

    
    content.append(
        KeepTogether([
            Paragraph(
                "Future Capacity Predictions",
                centered_heading
            ),
            Spacer(1, 5),
            future_capacity_table,
            Spacer(1, 5),
            Paragraph(
                f"""
                Note: Projected appointments assume a {growth_rate*100}% 
                annual growth in completed appointments.
                Number of possible appointments calculated by the 
                average appointment duration plus a {turnover_time} 
                minute turnover times {exam_room_count} rooms across an entire year. 
                
                
                """,
                centered_note_style
            )
        ])
    )
    if year_85_percent is not None:
            content.append(
                Paragraph(
                    f"""85% utilization is reached in Year {year_85_percent}""",
                    centered_note_style
                )
            )
    else:
        content.append(
            Paragraph(
                f"""85% utilization was not reach in the time frame.""",
                centered_note_style
            )
        )

    content.append(PageBreak())

    content.append(Spacer(1, 10))

    
    assumption_data = [
        ["Model Assumptions/Constants"],
        [f"Exam rooms: {exam_room_count}"],
        [f"Optimal Capacity: {optimal_capacity}"],
        [f"Clinic hours: {open_time} - {close_time}"],
        [f"Turnover time: {turnover_time} minutes"],
        [f"Annual Growth Rate: {growth_rate*100}%"],
        [
            Paragraph(
                f"{appointments_to_exclude} not included in exam room analysis",
                styles["BodyText"]
            )
        ]
    ]


    assumption_table = Table(
        assumption_data,
        colWidths=[300]
    )

    assumption_table_style = [
        ("GRID", (0,0), (-1,-1), 0.5, None),
        ("BACKGROUND", (0,0), (-1,0), "#d3d3d3"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
    ]

    assumption_table.setStyle(TableStyle(assumption_table_style))

    content.append(
        Paragraph("Model Assumptions", centered_heading)
    )



    content.append(assumption_table)


    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self.pages = []

        def showPage(self):
            self.pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            page_count = len(self.pages)

            for page in self.pages:
                self.__dict__.update(page)
                self.draw_footer(page_count)
                canvas.Canvas.showPage(self)

            canvas.Canvas.save(self)

        def draw_footer(self, page_count):
            width, height = self._pagesize

            # Footer line
            self.setLineWidth(0.5)
            self.line(
                40,
                45,
                width - 40,
                45
            )

            # Page number
            self.setFont("Helvetica", 8)
            self.drawRightString(
                width - 40,
                25,
                f"Page {self._pageNumber} of {page_count}"
            )

    def add_logo(canvas, doc):
        width, height = doc.pagesize

        canvas.saveState()

        # Logo - Top Left
        image_path = "bhealth.png"
        image_width = 100
        image_height = 50

        canvas.drawImage(
            image_path,
            40,
            height - image_height - 40,
            width=image_width,
            height=image_height,
            mask="auto"
        )

        canvas.restoreState()
        
    doc = SimpleDocTemplate(
    output_path,
    pagesize=letter,
    topMargin=60,
    bottomMargin=60
    )
    
    
    doc.build(
        content,
        onFirstPage=add_logo,
        onLaterPages=add_logo,
        canvasmaker=NumberedCanvas
    )
    
    
    return output_path



#%%streamlit stuff

# Display logo/image at top


st.markdown(
    """
    <style>
    .stApp {
        background-color: #F5F7FA;
    }
    </style>
    """,
    unsafe_allow_html=True
)
col1, col2 = st.columns([1,5])

with col1:
    st.image("bhealth.png", width=100)

with col2:
    st.title("Clinic Capacity Analysis")

uploaded_file = st.file_uploader("Upload EPIC data for clinic you want to analyze.", type='csv')

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    clinic_name = str(st.text_input(
        "Clinic Name",
        value="My Clinic"
    ))
    
    # Find unique departments
    # Find unique departments
    department_list = df["Department"].dropna().unique()
    
    st.subheader("Enter FTEs for Each Department")
    
    department_fte = {}
    
    for dept in department_list:
    
        department_fte[dept] = {
            "name": dept,
            "fte": st.number_input(
                f"Enter FTE for {dept}",
                min_value=0.0,
                value=1.0,
                step=0.1,
                key=f"fte_{dept}"
            )
        }

  
    # Clinic assumptions
    st.subheader("Clinic Capacity Assumptions")
    
    # Number of rooms
    exam_room_count = int(st.number_input(
        "Number of Exam Rooms",
        min_value=1,
        value=25,
        step=1
    ))
    
    #Clinic hours
    open_time = str(st.time_input(
        "Clinic Open Time",
        value=pd.Timestamp("08:00:00").time()
    ))
    
    # open_time = "08:00:00"
    # close_time = "17:00:00"
    
    close_time = str(st.time_input(
        "Clinic Close Time",
        value=pd.Timestamp("17:00:00").time()
    ))
    
    
    
    # Turnover time
    turnover_time = int(st.number_input(
        "Turnover Time Between Appointments (minutes)",
        min_value=0,
        value=15,
        step=5
    ))
    
    # Growth rate
    growth_rate = st.number_input(
        "Annual Appointment Growth Rate (%)",
        min_value=0.0,
        value=5.0,
        step=0.5
    )
    
    # Convert percentage to decimal
    growth_rate = growth_rate / 100
    
    # Appointment type exclusions
    st.subheader("Appointment Exclusions")
    
    appointment_types = (
        df["Visit Type"]
        .dropna()
        .unique()
        .tolist()
    )
    
    appointments_to_exclude = st.multiselect(
        "Select Appointment Types to Exclude from Exam Room Analysis",
        options=sorted(appointment_types),
        default=[]
    )
        
#inputs


    MFM_FTE = department_fte.get("BH BZN MFM", 0)
    URO_GYN_FTE = department_fte.get("BH BZN URO-GYN", 0)
    GYN_ONC_FTE = department_fte.get("BH BZN GYN-ONCO", 0)
    WOMENS_SPEC_FTE = department_fte.get("BH BZN WOMENS SPEC", 0)

    
    # -----------------------------
    # Validate inputs before running
    # -----------------------------
    
    inputs_complete = True
    missing_inputs = []
    
    # Clinic name check
    if not clinic_name.strip():
        inputs_complete = False
        missing_inputs.append("Clinic Name")
    
    # Department FTE check
    if len(department_fte) == 0:
        inputs_complete = False
        missing_inputs.append("Department FTEs")
        
    for dept, info in department_fte.items():
        if info["fte"] <= 0:
            inputs_complete = False
            missing_inputs.append(f"FTE for {dept}")
        
    # Room count check
    if exam_room_count <= 0:
        inputs_complete = False
        missing_inputs.append("Number of Exam Rooms")
    
    # Time checks
    if open_time >= close_time:
        inputs_complete = False
        missing_inputs.append("Valid Clinic Hours")
    
    # Turnover check
    if turnover_time < 0:
        inputs_complete = False
        missing_inputs.append("Turnover Time")
    
    # Growth rate check
    if growth_rate < 0:
        inputs_complete = False
        missing_inputs.append("Growth Rate")
    

# -----------------------------
# Run Analysis Button
# -----------------------------
    
    if not inputs_complete:
        st.warning(
            "Please complete the following fields before running the analysis:\n\n"
            + "\n".join(missing_inputs)
        )
    
    run_analysis = st.button(
        "Run Capacity Analysis",
        disabled=not inputs_complete
    )
    
    
        
    # RUN ANALYSIS
    if run_analysis:
    
        status = st.empty()
        status.info("Running analysis...")
    
        results = analysis(
            df,
            clinic_name,
            department_fte,
            exam_room_count,
            growth_rate,
            open_time,
            close_time,
            turnover_time,
            appointments_to_exclude
        )
        
        
            
        data_start_date = results["data_start_date"].strftime("%B %d, %Y")
        data_end_date = results["data_end_date"].strftime("%B %d, %Y")
        provider_results = results["provider"]
        room_results = results["rooms"]
        no_show_table_data = results["no_show"]
        future_capacity_table_data = results["future"]
        year_85_percent = results['year_85_percent']

    
        # store results
        st.session_state["results"] = results
    
        status.success("Analysis Complete!")
    
    
    # -----------------------------
    # DISPLAY RESULTS (ALWAYS if AVAILABLE)
    # -----------------------------
    if "results" in st.session_state:
    
        results = st.session_state["results"]
        
                
        if "results" in st.session_state:
        
            results = st.session_state["results"]
        
            # PDF button appears here
            if st.button("Generate PDF Report"):
        
                pdf_path = create_capacity_pdf(
                    results=results,
                    clinic_name=clinic_name,
                    df=df,
                    turnover_time=turnover_time,
                    exam_room_count=exam_room_count
                )
        
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label="Download Report",
                        data=f,
                        file_name=f"{clinic_name}_Capacity_Report.pdf",
                        mime="application/pdf"
                    )

    
        tab1, tab2, tab3, tab4 = st.tabs([
            "Provider Capacity",
            "Room Utilization",
            "Appointment Summary",
            "Growth Predictions"
        ])
    
        with tab3:
            st.dataframe(
                pd.DataFrame(
                    results["no_show"][1:], 
                    columns=results["no_show"][0]
                )
            )
            st.pyplot(results["appointment_chart"])
    
        with tab1:
            st.dataframe(pd.DataFrame(
                results["provider"],
                columns=[
                    "Department",
                    "FTE",
                    "Avg. Appt. Length",
                    "Provider Capacity",
                    "Appts. Completed",
                    "Capacity %"
                ]
            ))
            
            st.info(
                f"Provider capacity is calculated by dividing the actual number of appointments conducted by the maximum number of appointments providers can complete based on 4-week average FTE, average appointment length, and a {turnover_time} minute turnover time for every appointment. Turnover time is not applied to the average appointment lengths seen here"

            )

    
        with tab2:
            st.dataframe(pd.DataFrame(
                results["rooms"],
                columns=["Metric","Hours","Percent"]
            ))
            st.info(
                f"Exam room utilization by time was determined by adding a {turnover_time} minute turnover to each appointment slot, and counting the number of exam rooms that are occupied simulatenously for every minute the clinic has been open within the given data range."

            )
    
        with tab4:
            st.dataframe(pd.DataFrame(
                
                results["future"][1:],
                columns=results["future"][0]

            ))
            
            if year_85_percent is not None:
                st.warning(
                    f"""
                   Given current operating conditions and a {growth_rate*100}% annual growth rate, capacity will be reached in {year_85_percent} years.
                    """
                )
            else:
                st.warning(
                    f"""
                   Given current operating conditions and a {growth_rate*100}% annual growth rate, capacity will not be reached for at least 20 years years.
                    """
                )
                
            st.info(
                f"""
                Note: Projected appointments assume a {growth_rate*100}% annual growth in completed appointments.
                Number of possible appointments calculated by the average appointment duration plus a {turnover_time} minute turnover times {exam_room_count} rooms across an entire year. 
                """

            )
            
            
