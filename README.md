# LodeStar

Preserving democracy through verified truth: Aggregating political statements and actions to inform voters and prevent decisions against their interests.

## Welcome to LodeStar!

We're building a decentralized platform to fight misinformation and preserve democracy through verified truth. We believe that an informed citizenry is the cornerstone of a healthy democracy, and we need your help to make this vision a reality.

LodeStar automatically collects, verifies, and presents political statements alongside their real-world outcomes, helping people see the difference between rhetoric and reality.

## Core Principles
- **Truth-First**: Only present verified facts without editorialization
- **Decentralized**: Hosted via IPFS to prevent takedowns
- **Historical Transparency**: Highlight historical government statements and their subsequent actions
- **Democracy Preservation**: Empowering voters with verified truth to make informed decisions that protect democratic values
- **Inclusive Participation**: Enable anonymous contribution to fighting misinformation
- **Non-Partisan**: Analyzes all government statements and actions
- **Transparent**: Publicly accessible data sources and methodology

## Data Sources
- Government press releases and official statements (including historical)
- Fact-checking platforms (Ground News, PolitiFact)
- News archives covering multiple administrations (including historical)
- Social media from all political figures
- Public policy documents and voting records
- Historical government statements and actions

## How It Works
1. **Distributed Crawling**: Volunteer-run crawlers collect information from various sources
2. **Verification**: All data is cryptographically signed for authenticity
3. **Storage**: Content is stored on IPFS for permanent, uncensorable access
4. **Presentation**: Verified information is displayed in an easy-to-understand format

## Project Structure
```
lodestar/
├── crawler/        # Decentralized web crawling infrastructure
├── processor/      # Text/video extraction pipeline
├── frontend/       # Static truth comparison interface
└── ipfs-deploy/    # Automated IPFS deployment workflow
```

## Volunteer Program
LodeStar is powered by volunteers like you! You can contribute in several ways:

### Run a Crawler Node
- Help collect data by running a crawler from your own machine
- All data is cryptographically signed for verification
- No public attribution required - you can contribute anonymously
- Data is stored directly on IPFS for permanent access

### Contribute to Development
- Help improve the codebase
- Add new features
- Fix bugs
- Improve documentation

### Spread the Word
- Share LodeStar with others
- Help raise awareness about the importance of verified information

See `frontend/volunteer.html` for detailed instructions on becoming a volunteer crawler.

## Installation and Setup

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Install IPFS:
   - Download and install IPFS Desktop from https://ipfs.tech/
   - Or install IPFS command-line tools from https://dist.ipfs.tech/#kubo

3. Start the IPFS daemon:
   ```
   ipfs daemon
   ```

## Running the Application

1. Start the WebSocket server:
   ```
   python websocket_server.py
   ```

2. Start the frontend server:
   ```
   cd frontend
   python -m http.server 8000
   ```

3. Access the application at http://localhost:8000

## Contributing

We welcome contributions from the community! LodeStar is a collaborative effort to preserve democracy through verified truth.

### How You Can Contribute
- **Code**: Help develop new features, fix bugs, or improve existing functionality
- **Crawlers**: Run a crawler node to help collect data
- **Documentation**: Improve our documentation to help others understand and use LodeStar
- **Testing**: Test the application and report issues
- **Design**: Help improve the user interface and user experience
- **Community**: Spread the word about LodeStar and its mission

### Getting Started
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

Please see our contribution guidelines for more detailed information.

## Community

Join our community of volunteers working to preserve democracy through verified truth:

- **GitHub Issues**: Report bugs or request features
- **Discussions**: Engage with other contributors and users

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For questions, suggestions, or support, please open an issue on GitHub.