#!/usr/bin/env python3
"""
Data Quality Monitoring for Revenue Management System
Ensures data consistency and alerts on quality issues
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def check_data_quality():
    """Comprehensive data quality checks"""
    
    print("=== DATA QUALITY MONITORING ===")
    
    # Load current dataset
    df = pd.read_csv("dataset_processed.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    
    quality_issues = []
    
    # 1. Date continuity check
    date_range = pd.date_range(df["Date"].min(), df["Date"].max(), freq="D")
    missing_dates = set(date_range) - set(df["Date"])
    if missing_dates:
        quality_issues.append(f"Missing dates: {len(missing_dates)} days")
    else:
        print("✅ Date continuity: GOOD")
    
    # 2. Room inventory consistency
    inventory_check = df.groupby("Room Type")["Room Inventory"].nunique()
    for room_type, unique_counts in inventory_check.items():
        if unique_counts > 1:
            quality_issues.append(f"Room inventory inconsistency: {room_type}")
        else:
            print(f"✅ {room_type} inventory: CONSISTENT")
    
    # 3. Rate reasonableness check
    for room_type in df["Room Type"].unique():
        room_rates = df[df["Room Type"] == room_type]["Average Room Rate"].dropna()
        
        if len(room_rates) > 0:
            q1, q3 = room_rates.quantile([0.25, 0.75])
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outliers = room_rates[(room_rates < lower_bound) | (room_rates > upper_bound)]
            outlier_pct = len(outliers) / len(room_rates) * 100
            
            if outlier_pct > 5:  # More than 5% outliers
                quality_issues.append(f"{room_type} rate outliers: {outlier_pct:.1f}%")
            else:
                print(f"✅ {room_type} rates: REASONABLE ({outlier_pct:.1f}% outliers)")
    
    # 4. Occupancy logic check
    occupancy_issues = df[df["Occupancy Rate"] > 1.0]
    if len(occupancy_issues) > 0:
        quality_issues.append(f"Impossible occupancy (>100%): {len(occupancy_issues)} records")
    else:
        print("✅ Occupancy rates: LOGICAL")
    
    # 5. Segment consistency check
    excluded_segments = ["LGSTAY", "COMP", "HU"]
    for room_type in df["Room Type"].unique():
        room_data = df[df["Room Type"] == room_type]
        max_sold = room_data["Rooms Sold"].max()
        inventory = room_data["Room Inventory"].iloc[0]
        
        if max_sold > inventory:
            quality_issues.append(f"{room_type}: Rooms sold ({max_sold}) > Inventory ({inventory})")
        else:
            print(f"✅ {room_type} sold/inventory: LOGICAL")
    
    # 6. Holiday data consistency
    holidays_df = pd.read_csv("holidays_info.csv")
    holidays_df["Date"] = pd.to_datetime(holidays_df["Date"])
    
    dataset_holidays = set(df[df["Is_Holiday"] == True]["Date"].dt.date)
    file_holidays = set(holidays_df[holidays_df["Kind"].isin(["national", "joint"])]["Date"].dt.date)
    
    missing_holidays = file_holidays - dataset_holidays
    extra_holidays = dataset_holidays - file_holidays
    
    if missing_holidays or extra_holidays:
        quality_issues.append(f"Holiday mismatch: {len(missing_holidays)} missing, {len(extra_holidays)} extra")
    else:
        print("✅ Holiday flags: CONSISTENT")
    
    # Summary
    print(f"\n=== QUALITY SUMMARY ===")
    if quality_issues:
        print("❌ ISSUES FOUND:")
        for issue in quality_issues:
            print(f"   - {issue}")
        return False
    else:
        print("✅ ALL CHECKS PASSED - DATA QUALITY GOOD")
        return True

def forecast_performance_check():
    """Check forecast performance trends"""
    
    print("\n=== FORECAST PERFORMANCE MONITORING ===")
    
    # Load forecast results
    forecast_df = pd.read_csv("forecasting_2026.csv")
    forecast_df["Date"] = pd.to_datetime(forecast_df["Date"])
    
    # Filter historical data with actuals
    hist_data = forecast_df[forecast_df["Average Room Rate"].notna()].copy()
    
    if len(hist_data) == 0:
        print("❌ No historical data found for performance check")
        return False
    
    # Calculate current performance
    hist_data["Error ARR"] = np.abs(hist_data["Average Room Rate"] - hist_data["Forecasted ARR"]) / hist_data["Average Room Rate"]
    
    overall_mape = hist_data["Error ARR"].mean() * 100
    
    print(f"Current Overall MAPE: {overall_mape:.2f}%")
    
    # Performance by room type
    print("\nRoom Type Performance:")
    for room_type in hist_data["Room Type"].unique():
        room_data = hist_data[hist_data["Room Type"] == room_type]
        room_mape = room_data["Error ARR"].mean() * 100
        print(f"   {room_type}: {room_mape:.1f}% MAPE")
    
    # Performance alerts
    alerts = []
    
    if overall_mape > 25:
        alerts.append(f"Overall MAPE too high: {overall_mape:.2f}%")
    
    for room_type in hist_data["Room Type"].unique():
        room_data = hist_data[hist_data["Room Type"] == room_type]
        room_mape = room_data["Error ARR"].mean() * 100
        
        if room_type == "Deluxe" and room_mape > 15:
            alerts.append(f"Deluxe MAPE degraded: {room_mape:.1f}%")
        elif room_type == "Executive Suite" and room_mape > 25:
            alerts.append(f"Executive Suite MAPE degraded: {room_mape:.1f}%")
        elif room_type in ["Suite", "Family Suite"] and room_mape > 40:
            alerts.append(f"{room_type} MAPE degraded: {room_mape:.1f}%")
    
    if alerts:
        print("\n❌ PERFORMANCE ALERTS:")
        for alert in alerts:
            print(f"   - {alert}")
        return False
    else:
        print("\n✅ FORECAST PERFORMANCE: GOOD")
        return True

def main():
    """Main monitoring function"""
    
    print("=" * 60)
    print("REVENUE MANAGEMENT SYSTEM - DATA QUALITY MONITOR")
    print(f"Run Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    data_quality_ok = check_data_quality()
    forecast_performance_ok = forecast_performance_check()
    
    print(f"\n{'='*60}")
    if data_quality_ok and forecast_performance_ok:
        print("🟢 SYSTEM STATUS: HEALTHY")
        print("   - Data quality: GOOD")
        print("   - Forecast performance: GOOD")
        print("   - No action required")
    else:
        print("🔴 SYSTEM STATUS: NEEDS ATTENTION")
        if not data_quality_ok:
            print("   - Data quality: ISSUES FOUND")
        if not forecast_performance_ok:
            print("   - Forecast performance: DEGRADED")
        print("   - Manual review recommended")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
