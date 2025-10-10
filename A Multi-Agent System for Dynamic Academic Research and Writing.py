

# 1. Install packages
!pip install arxiv pandas gradio plotly google-cloud-firestore -q

# 2. Import libraries
import arxiv
import pandas as pd
import datetime
import re
import gradio as gr
import plotly.express as px
import firebase_admin
from firebase_admin import credentials, firestore
import json
import tempfile
import os
from google.colab import files

print("✅ All packages installed and imported successfully!")

# 3. Global variables
db = None
research_pipeline = None
current_research_data = []

# 4. Firebase Setup Function
def setup_firebase(uploaded_file):
    global db, research_pipeline
    try:
        if uploaded_file is None:
            return "❌ Please upload Firebase service account JSON file"
        
        # Clean up any existing Firebase apps
        try:
            for app in firebase_admin._apps.values():
                firebase_admin.delete_app(app)
        except:
            pass
        
        # Save the uploaded file
        with open("service_account.json", "wb") as f:
            f.write(uploaded_file)
        
        # Initialize Firebase
        cred = credentials.Certificate("service_account.json")
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        research_pipeline = ResearchDataPipeline(db)
        
        return "✅ Firebase initialized successfully! Database is ready."
        
    except Exception as e:
        return f"❌ Error initializing Firebase: {str(e)}"

# 5. Academic Data Collection Class (arXiv Only)
class AcademicDataCollector:
    def _init_(self):
        pass
        
    def search_arxiv_papers(self, query, max_results=10):
        """Search for research papers on arXiv"""
        try:
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance
            )
            papers = []
            for result in search.results():
                paper_data = {
                    'paper_id': result.entry_id.split('/')[-1],
                    'title': result.title,
                    'authors': [str(author) for author in result.authors],
                    'abstract': result.summary,
                    'published': result.published,
                    'pdf_url': result.pdf_url,
                    'primary_category': result.primary_category,
                    'categories': result.categories,
                    'source': 'arxiv'
                }
                papers.append(paper_data)
            return papers
        except Exception as e:
            print(f"❌ Error searching arXiv: {e}")
            return []
    
    def get_research_data(self, research_topic, max_papers=10):
        """Get research data from arXiv"""
        return self.search_arxiv_papers(research_topic, max_papers)

# 6. Research Data Cleaning Class
class ResearchDataCleaner:
    def _init_(self):
        self.cleaning_log = []
    
    def clean_research_papers(self, papers_data):
        """Clean and standardize research paper data"""
        cleaned_papers = []
        for paper in papers_data:
            try:
                cleaned_paper = {
                    'paper_id': self._generate_paper_id(paper),
                    'title': self._clean_text(paper.get('title', '')),
                    'authors': self._clean_authors(paper.get('authors', [])),
                    'abstract': self._clean_abstract(paper.get('abstract', '')),
                    'published_date': self._parse_date(paper.get('published', '')),
                    'url': paper.get('pdf_url', ''),
                    'source': paper.get('source', 'arxiv'),
                    'categories': paper.get('categories', []),
                    'primary_category': paper.get('primary_category', ''),
                    'keywords': self._extract_keywords(paper.get('abstract', '')),
                    'abstract_word_count': len(paper.get('abstract', '').split()),
                    'cleaned_at': datetime.datetime.now(),
                    'data_quality_score': self._calculate_quality_score(paper)
                }
                cleaned_papers.append(cleaned_paper)
            except Exception as e:
                continue
        return cleaned_papers
    
    def _generate_paper_id(self, paper):
        if paper.get('paper_id'):
            return paper['paper_id']
        else:
            title_hash = hash(paper.get('title', '')) % 10000
            return f"paper_{abs(title_hash)}"
    
    def _clean_text(self, text):
        if not text: 
            return ""
        return re.sub(r'\s+', ' ', str(text)).strip()
    
    def _clean_authors(self, authors):
        cleaned_authors = []
        for author in authors:
            if author:
                clean_author = self._clean_text(author)
                if clean_author and clean_author not in cleaned_authors:
                    cleaned_authors.append(clean_author)
        return cleaned_authors
    
    def _clean_abstract(self, abstract):
        if not abstract: 
            return ""
        clean_abstract = re.sub(r'<[^>]+>', '', abstract)
        return self._clean_text(clean_abstract)
    
    def _parse_date(self, date_str):
        try:
            if isinstance(date_str, datetime.datetime): 
                return date_str
            if not date_str: 
                return datetime.datetime.now()
            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y']:
                try: 
                    return datetime.datetime.strptime(date_str[:10], fmt)
                except ValueError: 
                    continue
            return datetime.datetime.now()
        except: 
            return datetime.datetime.now()
    
    def _extract_keywords(self, abstract, max_keywords=10):
        if not abstract: 
            return []
        words = abstract.lower().split()
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        keywords = [word for word in words if len(word) > 3 and word not in stop_words]
        return list(set(keywords))[:max_keywords]
    
    def _calculate_quality_score(self, paper):
        score = 0
        if paper.get('title'): 
            score += 20
        if paper.get('authors'): 
            score += 20
        abstract = paper.get('abstract', '')
        if abstract and len(abstract.split()) > 10: 
            score += 30
        if paper.get('published'): 
            score += 15
        if paper.get('pdf_url'): 
            score += 15
        return score

# 7. Research Database Manager
class ResearchDatabaseManager:
    def _init_(self, db):
        self.db = db
        self.collections = {
            'research_papers': 'research_papers',
            'research_sessions': 'research_sessions',
            'research_topics': 'research_topics'
        }
    
    def store_research_papers(self, papers_data, research_topic, session_id=None):
        """Store research papers in Firestore database"""
        if not papers_data: 
            return False, "No papers data to store"
        
        batch = self.db.batch()
        success_count = 0
        
        for paper in papers_data:
            try:
                # Use paper_id as document ID
                doc_id = paper['paper_id']
                doc_ref = self.db.collection(self.collections['research_papers']).document(doc_id)
                
                # Add metadata
                paper['research_topic'] = research_topic
                paper['session_id'] = session_id
                paper['stored_at'] = datetime.datetime.now()
                
                batch.set(doc_ref, paper)
                success_count += 1
            except Exception as e: 
                print(f"Error storing paper {paper['paper_id']}: {e}")
                continue
        
        try:
            batch.commit()
            
            # Store session info
            if session_id:
                session_data = {
                    'session_id': session_id,
                    'research_topic': research_topic,
                    'paper_count': success_count,
                    'created_at': datetime.datetime.now(),
                    'status': 'completed'
                }
                session_ref = self.db.collection(self.collections['research_sessions']).document(session_id)
                session_ref.set(session_data)
            
            return True, f"Successfully stored {success_count} research papers in database"
            
        except Exception as e: 
            return False, f"Error storing papers in database: {e}"
    
    def get_database_stats(self):
        """Get statistics about the research database"""
        try:
            papers_ref = self.db.collection(self.collections['research_papers'])
            papers = list(papers_ref.limit(1000).stream())
            
            # Count by source and category
            sources = {}
            categories = {}
            total_papers = len(papers)
            
            for paper in papers:
                paper_data = paper.to_dict()
                source = paper_data.get('source', 'unknown')
                category = paper_data.get('primary_category', 'unknown')
                
                sources[source] = sources.get(source, 0) + 1
                categories[category] = categories.get(category, 0) + 1
            
            return {
                'total_papers': total_papers,
                'papers_by_source': sources,
                'papers_by_category': categories
            }
            
        except Exception as e: 
            return {'error': str(e)}
    
    def get_recent_research_sessions(self, limit=5):
        """Get recent research sessions"""
        try:
            sessions_ref = self.db.collection(self.collections['research_sessions'])
            sessions = sessions_ref.order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit).stream()
            
            recent_sessions = []
            for session in sessions:
                session_data = session.to_dict()
                recent_sessions.append(session_data)
            
            return recent_sessions
        except Exception as e:
            return []

# 8. Complete Research Pipeline
class ResearchDataPipeline:
    def _init_(self, db):
        self.data_collector = AcademicDataCollector()
        self.data_cleaner = ResearchDataCleaner()
        self.db_manager = ResearchDatabaseManager(db)
    
    def run_pipeline(self, research_topic, max_papers=10):
        try:
            # Data Collection
            raw_data = self.data_collector.get_research_data(research_topic, max_papers)
            if not raw_data: 
                return None, "No research data found for the given topic"
            
            # Data Cleaning
            cleaned_data = self.data_cleaner.clean_research_papers(raw_data)
            
            # Generate session ID
            session_id = f"session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Database Storage
            success, message = self.db_manager.store_research_papers(cleaned_data, research_topic, session_id)
            
            if success:
                # Get updated database stats
                stats = self.db_manager.get_database_stats()
                db_message = f" | Database now has {stats.get('total_papers', 0)} total papers"
                return cleaned_data, f"✅ {message}{db_message}"
            else: 
                return cleaned_data, f"⚠ Data collected but database storage failed: {message}"
                
        except Exception as e: 
            return None, f"❌ Pipeline error: {str(e)}"

# 9. Visualization Functions
def create_research_visualizations(papers_data):
    if not papers_data: 
        return None, None
    df = pd.DataFrame(papers_data)
    
    # Visualization 1: Papers by Category
    category_counts = df['primary_category'].value_counts().head(8)
    fig1 = px.pie(
        values=category_counts.values, 
        names=category_counts.index, 
        title="Research Papers by Primary Category"
    )
    
    # Visualization 2: Quality Score Distribution
    fig2 = px.histogram(
        df, 
        x='data_quality_score', 
        title="Data Quality Score Distribution",
        nbins=10,
        color_discrete_sequence=['#3366CC']
    )
    
    return fig1, fig2

def generate_research_report(papers_data):
    if not papers_data: 
        return "No data available for report generation"
    
    df = pd.DataFrame(papers_data)
    
    report = f"""
📊 ARXIV RESEARCH DATA ANALYSIS REPORT
=====================================

Data Collection Summary:
• Total Papers Collected: {len(df)}
• Average Quality Score: {df['data_quality_score'].mean():.1f}/100
• Average Abstract Length: {df['abstract_word_count'].mean():.1f} words
• Date Range: {df['published_date'].min().strftime('%Y-%m-%d')} to {df['published_date'].max().strftime('%Y-%m-%d')}

Top Categories:"""
    
    for category, count in df['primary_category'].value_counts().head(5).items():
        report += f"\n    • {category}: {count} papers"
    
    report += f"""

Quality Assessment:
• Excellent (80-100): {len(df[df['data_quality_score'] >= 80])} papers
• Good (60-79): {len(df[(df['data_quality_score'] >= 60) & (df['data_quality_score'] < 80)])} papers
• Fair (40-59): {len(df[(df['data_quality_score'] >= 40) & (df['data_quality_score'] < 60)])} papers
• Poor (<40): {len(df[df['data_quality_score'] < 40])} papers

Sample Papers (with PDF links):"""
    
    # Show top 3 papers by quality score
    top_papers = df.nlargest(3, 'data_quality_score')
    for i, (_, paper) in enumerate(top_papers.iterrows(), 1):
        pdf_link = paper.get('url', 'No PDF available')
        report += f"""
{i}. {paper['title'][:70]}...
   - Authors: {', '.join(paper['authors'][:2])}...
   - Category: {paper['primary_category']}
   - Quality Score: {paper['data_quality_score']}/100
   - PDF: {pdf_link}
"""
    
    return report

# 10. Database Management Functions
def get_database_info():
    global db
    if db is None:
        return "❌ Database not initialized. Please setup Firebase first."
    
    try:
        db_manager = ResearchDatabaseManager(db)
        stats = db_manager.get_database_stats()
        
        if 'error' in stats:
            return f"❌ Error accessing database: {stats['error']}"
        
        info = f"""
📊 DATABASE INFORMATION
=====================

Total Papers Stored: {stats.get('total_papers', 0)}

Papers by Source:"""
        
        for source, count in stats.get('papers_by_source', {}).items():
            info += f"\n• {source}: {count} papers"
        
        info += f"\n\nTop Categories:"
        categories = stats.get('papers_by_category', {})
        for category, count in list(categories.items())[:5]:
            info += f"\n• {category}: {count} papers"
        
        # Get recent sessions
        recent_sessions = db_manager.get_recent_research_sessions(3)
        if recent_sessions:
            info += f"\n\nRecent Research Sessions:"
            for i, session in enumerate(recent_sessions, 1):
                info += f"\n{i}. {session.get('research_topic', 'Unknown')} - {session.get('paper_count', 0)} papers"
        
        return info
        
    except Exception as e:
        return f"❌ Error getting database info: {str(e)}"

# 11. Main Processing Function - UPDATED FOR PROPER LINKS
def process_research_topic(research_topic, max_papers):
    global research_pipeline, current_research_data
    
    if research_pipeline is None:
        return "❌ Database not initialized. Please setup Firebase first.", None, None, None, None
    
    papers_data, message = research_pipeline.run_pipeline(research_topic, max_papers)
    current_research_data = papers_data
    
    if papers_data is None: 
        return message, None, None, None, None
    
    fig1, fig2 = create_research_visualizations(papers_data)
    report = generate_research_report(papers_data)
    
    # Create display table with proper URL handling
    df_display = pd.DataFrame(papers_data)
    display_columns = ['title', 'primary_category', 'data_quality_score', 'abstract_word_count', 'url', 'source']
    
    # Ensure all required columns exist
    available_columns = [col for col in display_columns if col in df_display.columns]
    df_display = df_display[available_columns]
    
    # Format the display - show clean URLs instead of HTML
    df_display['title'] = df_display['title'].str[:60] + '...'
    df_display['url'] = df_display['url'].apply(lambda x: x if pd.notna(x) else 'No PDF')
    
    return message, df_display, fig1, fig2, report

# Function to create clickable HTML table
def create_clickable_table(papers_data):
    """Create an HTML table with clickable links"""
    if not papers_data:
        return "<p>No data available</p>"
    
    df = pd.DataFrame(papers_data)
    
    # Create HTML table
    html_table = """
    <style>
    .research-table {
        width: 100%;
        border-collapse: collapse;
        font-family: Arial, sans-serif;
    }
    .research-table th, .research-table td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    .research-table th {
        background-color: #f2f2f2;
        font-weight: bold;
    }
    .research-table tr:nth-child(even) {
        background-color: #f9f9f9;
    }
    .pdf-link {
        color: #3366cc;
        text-decoration: none;
        font-weight: bold;
    }
    .pdf-link:hover {
        text-decoration: underline;
    }
    </style>
    <table class="research-table">
        <thead>
            <tr>
                <th>Title</th>
                <th>Category</th>
                <th>Quality Score</th>
                <th>Abstract Words</th>
                <th>PDF Link</th>
                <th>Source</th>
            </tr>
        </thead>
        <tbody>
    """
    
    for _, paper in df.iterrows():
        title = paper.get('title', '')[:60] + '...' if len(paper.get('title', '')) > 60 else paper.get('title', '')
        category = paper.get('primary_category', 'Unknown')
        quality_score = paper.get('data_quality_score', 0)
        word_count = paper.get('abstract_word_count', 0)
        url = paper.get('url', '')
        source = paper.get('source', 'arxiv')
        
        pdf_link = f'<a href="{url}" class="pdf-link" target="_blank">📄 Open PDF</a>' if url else 'No PDF'
        
        html_table += f"""
        <tr>
            <td>{title}</td>
            <td>{category}</td>
            <td>{quality_score}</td>
            <td>{word_count}</td>
            <td>{pdf_link}</td>
            <td>{source}</td>
        </tr>
        """
    
    html_table += """
        </tbody>
    </table>
    """
    
    return html_table

# 12. Create Gradio Interface - UPDATED WITH HTML TABLE
with gr.Blocks(theme=gr.themes.Soft(), title="arXiv Research Data Management") as demo:
    gr.Markdown("# 🎓 Academic Research Data Management System")
    gr.Markdown("### Module 1: Data Collection & Database Storage")
    
    with gr.Tab("🔧 Setup"):
        gr.Markdown("### Step 1: Database Setup")
        gr.Markdown("Upload your Firebase service account JSON file to initialize the database.")
        
        with gr.Row():
            firebase_file = gr.File(
                label="Upload Firebase Service Account JSON", 
                file_types=[".json"],
                type="binary"
            )
            setup_btn = gr.Button("Initialize Database", variant="primary")
        
        setup_output = gr.Textbox(
            label="Setup Status", 
            interactive=False,
            placeholder="Upload Firebase JSON file and click 'Initialize Database'"
        )
        
        setup_btn.click(fn=setup_firebase, inputs=[firebase_file], outputs=[setup_output])
    
    with gr.Tab("🔍 Research"):
        gr.Markdown("### Step 2: Collect & Store Research Data")
        gr.Markdown("Enter a research topic to collect papers from arXiv and store in database.")
        
        with gr.Row():
            research_input = gr.Textbox(
                label="Research Topic", 
                placeholder="e.g., machine learning climate change, quantum computing, neural networks...", 
                lines=2,
                scale=3
            )
            paper_slider = gr.Slider(
                minimum=5, 
                maximum=15, 
                value=8, 
                step=1, 
                label="Papers to Collect",
                scale=1
            )
        
        research_btn = gr.Button("🚀 Collect & Store Research Data", variant="primary", size="lg")
        
        status_output = gr.Textbox(
            label="Processing Status", 
            interactive=False
        )
        
        # Note about the table display
        gr.Markdown("📎 *Note:* Click on the 'Open PDF' links in the table below to open research papers in a new tab")
        
        # HTML output for clickable table
        html_output = gr.HTML(
            label="Research Papers with Clickable PDF Links",
            value="<p>Research results will appear here...</p>"
        )
        
        # Keep the dataframe for data display (optional)
        data_table = gr.Dataframe(
            label="Raw Data Preview", 
            interactive=False,
            visible=False  # Hide the regular dataframe since we're using HTML
        )
        
        with gr.Row():
            viz1 = gr.Plot(label="Papers by Category")
            viz2 = gr.Plot(label="Quality Score Distribution")
        
        report_output = gr.Textbox(
            label="Research Analysis Report", 
            lines=12, 
            interactive=False
        )
        
        def process_with_html_table(research_topic, max_papers):
            global research_pipeline, current_research_data
            
            if research_pipeline is None:
                return "❌ Database not initialized. Please setup Firebase first.", "<p>Please initialize database first</p>", None, None, None, None
            
            papers_data, message = research_pipeline.run_pipeline(research_topic, max_papers)
            current_research_data = papers_data
            
            if papers_data is None: 
                return message, "<p>No papers found</p>", None, None, None, None
            
            fig1, fig2 = create_research_visualizations(papers_data)
            report = generate_research_report(papers_data)
            
            # Create HTML table with clickable links
            html_table = create_clickable_table(papers_data)
            
            # Also create regular dataframe for backup
            df_display = pd.DataFrame(papers_data)
            display_columns = ['title', 'primary_category', 'data_quality_score', 'abstract_word_count', 'url', 'source']
            available_columns = [col for col in display_columns if col in df_display.columns]
            df_display = df_display[available_columns]
            df_display['title'] = df_display['title'].str[:60] + '...'
            
            return message, html_table, df_display, fig1, fig2, report
        
        research_btn.click(
            fn=process_with_html_table, 
            inputs=[research_input, paper_slider], 
            outputs=[status_output, html_output, data_table, viz1, viz2, report_output]
        )
    
    with gr.Tab("📊 Database"):
        gr.Markdown("### Step 3: Database Information")
        gr.Markdown("View statistics and information about your research database.")
        
        db_refresh_btn = gr.Button("🔄 Refresh Database Info", variant="secondary")
        db_info_output = gr.Textbox(
            label="Database Information", 
            lines=15, 
            interactive=False
        )
        
        db_refresh_btn.click(fn=get_database_info, outputs=[db_info_output])
    
    with gr.Tab("ℹ About"):
        gr.Markdown("""
        ## About This System
        
        *Module 1: Data Management* - With Database Storage
        
        *Features:*
        - 📚 Collects research papers from arXiv
        - 🗄 Stores data in Firebase Firestore database
        - 🧹 Cleans and validates academic data
        - 📊 Provides analysis and visualizations
        - 📈 Tracks research sessions and statistics
        - 🔗 Includes direct PDF links to research papers
        
        *Database Collections:*
        - research_papers - All collected papers with metadata
        - research_sessions - Tracking of each research query
        - research_topics - Categorized research topics
        
        *How to Use:*
        1. *Setup*: Upload Firebase credentials
        2. *Research*: Collect and store papers (click PDF links to open papers)
        3. *Database*: View stored data and statistics
        
        *Example Research Topics:*
        - "machine learning climate change"
        - "quantum computing algorithms"
        - "deep learning healthcare"
        - "computer vision autonomous vehicles"
        """)

# 13. Launch the interface
print("🚀 Launching Academic Research Data Management System with Database...")
print("📁 This system includes Firebase Firestore database storage")
print("💡 Start with the 'Setup' tab to initialize the database")
print("🔗 PDF links are now clickable in the research results table!")
demo.launch(share=True, debug=True)
