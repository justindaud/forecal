import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

def analyze_arr_occupancy_relationship():
    """Analyze ARR vs Occupancy relationship per room type with trendlines"""
    
    print("=== ARR vs OCCUPANCY RELATIONSHIP ANALYSIS ===")
    
    # Load dataset
    df = pd.read_csv("data/dataset_processed.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    
    # Get daily occupancy (hotel-level)
    daily_occ = df.groupby("Date").agg({
        "Occupancy Rate": "first",
        "Is_Holiday": "first",
        "Is_Weekend": "first"
    }).reset_index()
    
    # Merge with room data
    df_with_occ = df.merge(daily_occ[["Date", "Occupancy Rate"]], on="Date", how="left", suffixes=("", "_daily"))
    df_with_occ = df_with_occ.rename(columns={"Occupancy Rate_daily": "Overall_Occupancy"})
    
    # Create holiday/weekday flag
    df_with_occ["Is_Holiday_Weekend"] = df_with_occ["Is_Holiday"] | df_with_occ["Is_Weekend"]
    
    # Room types
    room_types = ["Deluxe", "Executive Suite", "Suite", "Family Suite"]
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()
    
    # Colors for each room type
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    # Store correlation results
    correlation_results = []
    
    for i, room_type in enumerate(room_types):
        ax = axes[i]
        
        # Filter data for this room type
        room_data = df_with_occ[df_with_occ["Room Type"] == room_type].copy()
        
        # Remove rows with missing data
        room_data = room_data.dropna(subset=["Average Room Rate", "Overall_Occupancy"])
        
        if len(room_data) == 0:
            ax.text(0.5, 0.5, f'No data for {room_type}', ha='center', va='center', transform=ax.transAxes)
            continue
        
        # Separate holiday and weekday data
        holiday_data = room_data[room_data["Is_Holiday_Weekend"] == True]
        weekday_data = room_data[room_data["Is_Holiday_Weekend"] == False]
        
        # Plot data points
        if len(weekday_data) > 0:
            ax.scatter(weekday_data["Overall_Occupancy"], weekday_data["Average Room Rate"]/1e6, 
                      alpha=0.6, s=20, color=colors[i], marker='x', label=f'{room_type} Weekday')
        
        if len(holiday_data) > 0:
            ax.scatter(holiday_data["Overall_Occupancy"], holiday_data["Average Room Rate"]/1e6, 
                      alpha=0.8, s=30, color=colors[i], marker='o', label=f'{room_type} Holiday')
        
        # Calculate correlations
        overall_corr, _ = stats.pearsonr(room_data["Overall_Occupancy"], room_data["Average Room Rate"])
        holiday_corr, _ = stats.pearsonr(holiday_data["Overall_Occupancy"], holiday_data["Average Room Rate"]) if len(holiday_data) > 1 else (np.nan, np.nan)
        weekday_corr, _ = stats.pearsonr(weekday_data["Overall_Occupancy"], weekday_data["Average Room Rate"]) if len(weekday_data) > 1 else (np.nan, np.nan)
        
        # Store results
        correlation_results.append({
            "Room Type": room_type,
            "Overall Correlation": overall_corr,
            "Holiday Correlation": holiday_corr,
            "Weekday Correlation": weekday_corr,
            "Data Points": len(room_data),
            "Holiday Points": len(holiday_data),
            "Weekday Points": len(weekday_data)
        })
        
        # Fit linear trendline
        if len(room_data) > 1:
            # Linear regression
            slope, intercept, r_value, p_value, std_err = stats.linregress(room_data["Overall_Occupancy"], room_data["Average Room Rate"])
            x_trend = np.linspace(room_data["Overall_Occupancy"].min(), room_data["Overall_Occupancy"].max(), 100)
            y_trend = slope * x_trend + intercept
            ax.plot(x_trend, y_trend/1e6, '--', color='red', alpha=0.8, linewidth=2, 
                   label=f'Linear (r={overall_corr:.3f})')
            
            # Polynomial trendline (degree 2) using numpy
            try:
                # Fit polynomial: y = ax^2 + bx + c
                coeffs = np.polyfit(room_data["Overall_Occupancy"], room_data["Average Room Rate"], 2)
                x_poly = np.linspace(room_data["Overall_Occupancy"].min(), room_data["Overall_Occupancy"].max(), 100)
                y_poly_trend = np.polyval(coeffs, x_poly)
                ax.plot(x_poly, y_poly_trend/1e6, '-', color='orange', alpha=0.8, linewidth=2, 
                       label='Polynomial (deg=2)')
            except:
                pass
        
        # Formatting
        ax.set_xlabel('Overall Occupancy Rate')
        ax.set_ylabel('Average Room Rate (Million IDR)')
        ax.set_title(f'{room_type}\nOverall r={overall_corr:.3f}')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        
        # Set consistent y-axis limits
        ax.set_ylim(0, max(room_data["Average Room Rate"].max()/1e6 * 1.1, 1))
    
    plt.tight_layout()
    plt.savefig("data/arr_occupancy_analysis_updated.png", dpi=300, bbox_inches='tight')
    plt.show()
    
    # Create correlation summary
    corr_df = pd.DataFrame(correlation_results)
    corr_df.to_csv("data/arr_occupancy_correlations_updated.csv", index=False)
    
    print("\n=== CORRELATION ANALYSIS RESULTS ===")
    print(corr_df.to_string(index=False))
    
    # Additional analysis: Exponential relationship
    print("\n=== EXPONENTIAL RELATIONSHIP ANALYSIS ===")
    
    for room_type in room_types:
        room_data = df_with_occ[df_with_occ["Room Type"] == room_type].copy()
        room_data = room_data.dropna(subset=["Average Room Rate", "Overall_Occupancy"])
        
        if len(room_data) > 10:  # Need sufficient data
            # Log transformation for exponential fit
            log_arr = np.log(room_data["Average Room Rate"])
            occupancy = room_data["Overall_Occupancy"]
            
            # Fit exponential model: ARR = a * exp(b * occupancy)
            slope, intercept, r_value, p_value, std_err = stats.linregress(occupancy, log_arr)
            
            # Calculate exponential parameters
            a = np.exp(intercept)
            b = slope
            
            # Calculate R² for exponential model
            predicted_log_arr = slope * occupancy + intercept
            predicted_arr = np.exp(predicted_log_arr)
            ss_res = np.sum((room_data["Average Room Rate"] - predicted_arr) ** 2)
            ss_tot = np.sum((room_data["Average Room Rate"] - room_data["Average Room Rate"].mean()) ** 2)
            r_squared_exp = 1 - (ss_res / ss_tot)
            
            print(f"{room_type}:")
            print(f"  Exponential model: ARR = {a:.0f} * exp({b:.3f} * occupancy)")
            print(f"  R² (exponential): {r_squared_exp:.3f}")
            print(f"  Linear R²: {overall_corr**2:.3f}")
            print(f"  Exponential fit {'better' if r_squared_exp > overall_corr**2 else 'worse'} than linear")
            print()
    
    return corr_df

if __name__ == "__main__":
    results = analyze_arr_occupancy_relationship()
    print("Analysis completed. Files saved:")
    print("- arr_occupancy_analysis_updated.png")
    print("- arr_occupancy_correlations_updated.csv")
