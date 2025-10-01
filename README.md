# Revenue Management Dashboard

Modern full-stack application for hotel revenue management with intelligent pricing recommendations and forecasting.

## Features

- 🎯 **Intelligent Pricing Recommendations** - Data-driven pricing suggestions based on historical patterns
- 📅 **Interactive Calendar View** - Visual calendar with pricing information per room type
- 🔄 **Real-time Data Refresh** - Connect to Flask backend for live data updates
- 📊 **Advanced Filtering** - Filter by date range, room type, and arrangement
- 🎨 **Modern UI** - Built with Next.js 15, TypeScript, and Tailwind CSS
- 📱 **Responsive Design** - Works perfectly on desktop and mobile devices
- 🔐 **Authentication System** - JWT-based login with role management
- 📈 **Forecasting Calculator** - Date range calculator with year-over-year comparisons
- 🏨 **Multi-Room Support** - Support for Deluxe, Executive Suite, Suite, and Family Suite
- 📊 **Transparent Drivers** - Show holiday, event, and occupancy factors affecting pricing

## Tech Stack

### Frontend
- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Shadcn/ui + Radix UI
- **Icons**: Lucide React
- **Date Handling**: date-fns
- **Authentication**: JWT with HTTP-only cookies

### Backend
- **Framework**: Flask (Python)
- **Database**: PostgreSQL (optional, uses CSV for demo)
- **Authentication**: JWT tokens
- **Data Processing**: pandas, numpy
- **ML**: scikit-learn (Random Forest)
- **API**: RESTful endpoints with CORS support

## Getting Started

### Prerequisites

- Node.js 18+ installed
- Python 3.8+ installed
- Flask backend running on `http://localhost:5001`

### Installation

#### Backend Setup
1. Navigate to backend directory:
```bash
cd backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Start the Flask server:
```bash
python main.py
```

#### Frontend Setup
1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

### Login Credentials
- **Admin**: `admin` / `admin123`
- **User**: `user` / `user123`
- **Demo**: `demo` / `demo123`

## Project Structure

```
FORECAST/
├── backend/               # Flask backend
│   ├── app/              # Flask application
│   │   └── revenue_management_app.py
│   ├── scripts/          # Data processing scripts
│   │   ├── forecast.py   # ML forecasting
│   │   └── data_extraction.py
│   ├── data/             # CSV data files
│   ├── auth.py           # Authentication module
│   ├── main.py           # Backend entry point
│   └── requirements.txt  # Python dependencies
├── frontend/             # Next.js frontend
│   ├── src/
│   │   ├── app/          # Next.js App Router
│   │   │   ├── login/    # Login page
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx
│   │   ├── components/   # React components
│   │   │   ├── ui/       # Shadcn/ui components
│   │   │   └── calendar-first-dashboard.tsx
│   │   ├── lib/          # Utilities
│   │   │   ├── api.ts    # API client
│   │   │   ├── auth.ts   # Auth utilities
│   │   │   └── utils.ts
│   │   └── middleware.ts # Route protection
│   ├── package.json
│   └── next.config.js
└── .env                  # Environment variables
```

## API Integration

The frontend communicates with the Flask backend through these endpoints:

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Get current user info

### Data Endpoints
- `GET /api/recommendations` - Get pricing recommendations
- `GET /api/calendar/:year/:month` - Get calendar data
- `POST /api/refresh` - Refresh data from database
- `GET /api/room_types` - Get available room types

## Features Overview

### 1. Authentication & Security
- JWT-based authentication with HTTP-only cookies
- Role-based access control (Admin, User, Demo)
- Protected routes with automatic redirects
- Secure session management

### 2. Calendar Dashboard
- Interactive monthly calendar view
- Color-coded occupancy rates (red=low, green=high)
- Room type and arrangement filtering
- Holiday, event, and fasting day indicators
- Year-over-year comparison calendar

### 3. Pricing Calculator
- Date range selection with flexible picker
- Room type and arrangement filters
- Total ARR and per-night calculations
- Year-over-year comparisons
- Date flags summary (holidays, events, weekends)

### 4. Transparent Pricing Drivers
- Holiday impact indicators
- Event and school holiday flags
- Weekend and bridge day detection
- Occupancy rate predictions
- Distance to holiday calculations

### 5. Data Management
- Real-time data refresh from backend
- CSV-based data storage (no database required)
- Machine learning forecasting with Random Forest
- Historical and predicted data integration

## Configuration

### Environment Variables

#### Backend (.env)
```env
DATABASE_URL=your_database_url
PORT=5001
FRONTEND_URL=http://localhost:3000
BACKEND_URL=http://localhost:5001
JWT_SECRET=your_jwt_secret_key_here
```

#### Frontend (frontend/.env)
```env
NEXT_PUBLIC_API_URL=http://localhost:5001
```

### Configuration Files
- `next.config.js` - Next.js configuration and API proxy
- `tsconfig.json` - TypeScript configuration with path aliases
- `middleware.ts` - Route protection and authentication

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

### API Client

The `apiClient` in `src/lib/api.ts` handles all backend communication with proper TypeScript interfaces and error handling.

## Deployment

1. Build the application:
```bash
npm run build
```

2. Start the production server:
```bash
npm run start
```

The application will be available at `http://localhost:3000`.

## Backend Integration

gunicorn -b 0.0.0.0:5001 app.revenue_management_app:app

This frontend is designed to work with the Flask backend (`revenue_management_app.py`). Make sure the Flask server is running on `http://localhost:5001` before starting the Next.js development server.

### Data Pipeline
1. **Data Extraction** - Extract historical data from CSV files
2. **Forecasting** - Apply machine learning models for predictions
3. **Data Processing** - Combine historical and predicted data
4. **API Serving** - Serve processed data through REST endpoints

### Machine Learning
- **Algorithm**: Random Forest Regressor
- **Features**: Calendar features, holiday indicators, occupancy patterns
- **Output**: Occupancy rates and ARR predictions
- **Transparency**: Driver analysis for pricing decisions

## Contributing

1. Follow TypeScript best practices
2. Use the existing component patterns
3. Maintain responsive design principles
4. Add proper error handling for API calls
5. Test authentication flows
6. Update environment variables as needed

## License

This project is for educational and demonstration purposes.