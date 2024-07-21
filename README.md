# RU Menu Getter and Data Analysis

This project automates the process of fetching daily menus from various university restaurants (RUs) and performing data analysis on the collected data. The data is then sent to Firebase to be used in the CampusDine app.

## Features

- **Daily Menu Fetching**: The script fetches daily menus from multiple universities, including UFABC, UFPR, and UFRGS.
- **Data Archiving**: The fetched menu data is archived in Firebase Realtime Database and Google Cloud Firestore.
- **Data Analysis**: Automated workflows perform data analysis on the archived menu data. (Not functional yet)
- **GitHub Actions Integration**: The entire process is automated using GitHub Actions, ensuring that the data is updated daily at midnight.

## Workflows

### Daily Menu Update

This workflow runs daily at 11:30 PM UTC to fetch and archive the daily menus.

- **Configuration**: [`.github/workflows/daily_menu.yml`](.github/workflows/daily_menu.yml)
- **Scripts**:
  - [`UFABC.rb`](UFABC.rb): Fetches the daily menu for UFABC.
  - [`UFPR.rb`](UFPR.rb): Fetches the daily menu for UFPR.
  - [`UFRGS.rb`](UFRGS.rb): Fetches the daily menu for UFRGS.
  - [`movedata_today.rb`](movedata_today.rb): Archives today's menu data to Firebase Realtime Database and Firestore to be used by Amazon Alexa.

### Data Analysis

This workflow can be manually triggered to perform data analysis on the archived menu data.

- **Configuration**: [`.github/workflows/data_analysis.yml`](.github/workflows/data_analysis.yml)
- **Script**: [`data_analysis.py`](data_analysis.py)

## Usage

### GitHub Actions Workflows

- **Daily Menu Update**: This workflow runs daily at 11:30 PM UTC to fetch and archive the daily menus.
  - Configuration: [`.github/workflows/daily_menu.yml`](.github/workflows/daily_menu.yml)

- **Data Analysis**: This workflow can be manually triggered to perform data analysis.
  - Configuration: [`.github/workflows/data_analysis.yml`](.github/workflows/data_analysis.yml)

## Environment Variables

The following environment variables are required for the scripts and workflows:

- `FIREBASE_KEY`: Firebase secret key.
- `BASE_URL`: Base URL for Firebase.
- `GCLOUD_PROJECT_ID`: Google Cloud project ID.
- `GCLOUD_ADMIN`: Google Cloud admin credentials.
- `SERVICE_ACCOUNT_CREDENTIALS`: Service account credentials for Google Cloud.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes.

## License

This project's license is available on the [LICENSE](LICENSE) file.
