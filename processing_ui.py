#!/usr/bin/env python3
"""
ArticleForge Article Processing System — Interactive CLI

A beautiful, interactive interface for managing your Harvard Business Review
article collection. Process PDFs, search metadata, export data, and more.

Usage:
    python hbr.py
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict

# ANSI Color codes
class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'


class ArticleForgeCLi:
    """Interactive CLI for ArticleForge article processing"""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.scripts_dir = self.base_dir / "scripts"
        self.output_dir = self.base_dir / "output"
        self.intake_dir = self.base_dir / "intake"
        self.archive_dir = self.base_dir / "pdf_archive"
        self.metadata_dir = self.base_dir / "metadata"

    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.ENDC}\n")

    def print_section(self, text: str):
        """Print formatted section"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}▶ {text}{Colors.ENDC}")
        print(f"{Colors.BLUE}{'-' * len(text) + '---'}{Colors.ENDC}\n")

    def print_success(self, text: str):
        """Print success message"""
        print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

    def print_info(self, text: str):
        """Print info message"""
        print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")

    def print_warning(self, text: str):
        """Print warning message"""
        print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")

    def print_error(self, text: str):
        """Print error message"""
        print(f"{Colors.RED}✗ {text}{Colors.ENDC}")

    def get_stats(self) -> Dict:
        """Get current system statistics"""
        stats = {
            'markdown_files': len(list(self.output_dir.glob('*.md'))),
            'archived_pdfs': len(list(self.archive_dir.glob('*.pdf'))),
            'intake_pdfs': len(list(self.intake_dir.glob('*.pdf'))),
            'total_articles': 0,
            'keywords': 0,
        }

        # Load metadata if available
        metadata_file = self.metadata_dir / "articles_metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    data = json.load(f)
                    articles = data.get('articles', [])
                    stats['total_articles'] = len(articles)
                    all_keywords = []
                    for article in articles:
                        all_keywords.extend(article.get('keywords', []))
                    stats['keywords'] = len(set(all_keywords))
            except:
                pass

        return stats

    def show_dashboard(self):
        """Show system dashboard"""
        self.print_header("📊 ArticleForge Article Processing System")

        stats = self.get_stats()

        # Status boxes
        print(f"{Colors.BOLD}System Status:{Colors.ENDC}\n")

        print(f"  {Colors.GREEN}●{Colors.ENDC} Markdown Files:    {Colors.BOLD}{stats['markdown_files']}{Colors.ENDC}")
        print(f"  {Colors.GREEN}●{Colors.ENDC} Archived PDFs:     {Colors.BOLD}{stats['archived_pdfs']}{Colors.ENDC}")
        print(f"  {Colors.GREEN}●{Colors.ENDC} Intake PDFs:       {Colors.BOLD}{stats['intake_pdfs']}{Colors.ENDC}")
        print(f"  {Colors.GREEN}●{Colors.ENDC} Total Articles:    {Colors.BOLD}{stats['total_articles']}{Colors.ENDC}")
        print(f"  {Colors.GREEN}●{Colors.ENDC} Unique Keywords:   {Colors.BOLD}{stats['keywords']}{Colors.ENDC}")

        print()

    def show_menu(self):
        """Display main menu"""
        menu_items = [
            ("1", "📥 Process Articles", "Extract & organize PDFs from intake/"),
            ("2", "🔍 Search Articles", "Find articles by keyword or author"),
            ("3", "📋 View Statistics", "Show metadata and keyword analysis"),
            ("4", "📤 Export Data", "Export to CSV or JSON"),
            ("5", "🔗 Export to Zotero", "Push articles to Zotero library"),
            ("6", "✏️  Metadata & Overrides", "Fix missing author & metadata issues"),
            ("7", "🏷️  Rename PDFs", "Rename archived PDFs to match markdown"),
            ("8", "📖 List All Articles", "Show all processed articles"),
            ("9", "🎯 Quick Preview", "Sample text from an article"),
            ("0", "⚙️  Settings", "Configure system options"),
            ("!", "❌ Exit", "Quit the program"),
        ]

        print(f"{Colors.BOLD}Main Menu:{Colors.ENDC}\n")
        for code, label, desc in menu_items:
            print(f"  {Colors.CYAN}{code}{Colors.ENDC}  {label:<30} {Colors.DIM}{desc}{Colors.ENDC}")

        print()

    def menu_process_articles(self):
        """Menu option: Process articles"""
        self.print_section("Process Articles from intake/")

        intake_count = len(list(self.intake_dir.glob('*.pdf')))
        if intake_count == 0:
            self.print_warning("No PDFs found in intake/ folder")
            input(f"\n{Colors.DIM}Press Enter to return to menu...{Colors.ENDC}")
            return

        self.print_info(f"Found {intake_count} PDFs to process")
        print(f"\n{Colors.DIM}Processing may take 1-2 minutes for large batches...{Colors.ENDC}\n")

        print("Options:")
        print(f"  1. Full processing (extract, organize, archive)")
        print(f"  2. Dry run (preview without saving)")
        print(f"  0. Cancel")
        print()

        choice = input(f"{Colors.CYAN}Select option (0-2): {Colors.ENDC}").strip()

        if choice == "0":
            return
        elif choice == "1":
            self._run_processor(dry_run=False)
        elif choice == "2":
            self._run_processor(dry_run=True)
        else:
            self.print_error("Invalid option")

        input(f"\n{Colors.DIM}Press Enter to return to menu...{Colors.ENDC}")

    def _run_processor(self, dry_run: bool = False):
        """Run the article processor"""
        try:
            cmd = [sys.executable, str(self.scripts_dir / "process_articles.py")]
            if dry_run:
                cmd.append("--dry-run")

            print(f"\n{Colors.DIM}Running processor...{Colors.ENDC}\n")
            result = subprocess.run(cmd, cwd=str(self.scripts_dir))

            if result.returncode == 0:
                self.print_success("Processing completed successfully!")
            else:
                self.print_error("Processing encountered errors")
        except Exception as e:
            self.print_error(f"Could not run processor: {e}")

    def menu_search_articles(self):
        """Menu option: Search articles"""
        self.print_section("Search Articles")

        print("Search options:")
        print(f"  1. By keyword")
        print(f"  2. By author")
        print(f"  3. List all articles")
        print(f"  0. Back")
        print()

        choice = input(f"{Colors.CYAN}Select option (0-3): {Colors.ENDC}").strip()

        if choice == "0":
            return
        elif choice == "1":
            query = input(f"\n{Colors.CYAN}Enter keyword to search: {Colors.ENDC}").strip()
            if query:
                self._run_query(f"--by-keyword {query}")
        elif choice == "2":
            author = input(f"\n{Colors.CYAN}Enter author name: {Colors.ENDC}").strip()
            if author:
                self._run_query(f"--by-author {author}")
        elif choice == "3":
            self._run_query("--list")
        else:
            self.print_error("Invalid option")

        input(f"\n{Colors.DIM}Press Enter to return to menu...{Colors.ENDC}")

    def _run_query(self, args: str):
        """Run the query tool"""
        try:
            cmd = [sys.executable, str(self.scripts_dir / "query_metadata.py")] + args.split()
            print()
            subprocess.run(cmd, cwd=str(self.scripts_dir))
        except Exception as e:
            self.print_error(f"Could not run query: {e}")

    def menu_statistics(self):
        """Menu option: View statistics"""
        self.print_section("Article Statistics")

        try:
            self._run_query("--stats")
        except Exception as e:
            self.print_error(f"Could not retrieve statistics: {e}")

        input(f"\n{Colors.DIM}Press Enter to return to menu...{Colors.ENDC}")

    def menu_export_data(self):
        """Menu option: Export data"""
        self.print_section("Export Data")

        print("Export formats:")
        print(f"  1. CSV (Excel compatible)")
        print(f"  2. JSON (Integration ready)")
        print(f"  0. Cancel")
        print()

        choice = input(f"{Colors.CYAN}Select format (0-2): {Colors.ENDC}").strip()

        if choice == "1":
            self._run_query("--export csv")
            self.print_success("Exported to articles_export.csv")
        elif choice == "2":
            self._run_query("--export json")
            self.print_success("Exported to articles_export.json")
        elif choice != "0":
            self.print_error("Invalid option")

        input(f"\n{Colors.DIM}Press Enter to return to menu...{Colors.ENDC}")

    def menu_zotero_export(self):
        """Menu option: Export to Zotero"""
        self.print_section("Export Articles to Zotero")

        metadata_file = self.metadata_dir / "articles_metadata.json"
        if not metadata_file.exists():
            self.print_error("No articles in registry. Process some PDFs first.")
            input(f"\n{Colors.DIM}Press Enter to return to menu...{Colors.ENDC}")
            return

        try:
            with open(metadata_file, 'r') as f:
                data = json.load(f)
                article_count = len(data.get('articles', []))
        except:
            article_count = 0

        print(f"You have {Colors.BOLD}{article_count}{Colors.ENDC} articles ready to export.\n")
        print("Export formats:")
        print(f"  1. BibTeX (⭐ Recommended - native Zotero format)")
        print(f"  2. CSV (Excel compatible)")
        print(f"  3. JSON (Full metadata, good for integrations)")
        print(f"  4. All formats")
        print(f"  0. Cancel")
        print()

        choice = input(f"{Colors.CYAN}Select format (0-4): {Colors.ENDC}").strip()

        if choice == "0":
            pass
        elif choice in ["1", "4"]:
            try:
                cmd = [sys.executable, str(self.scripts_dir / "zotero_export.py"), "--export", "bibtex"]
                subprocess.run(cmd, cwd=str(self.scripts_dir))
                self.print_success(f"BibTeX export created in metadata/zotero_export.bib")
            except Exception as e:
                self.print_error(f"Could not export to BibTeX: {e}")

        if choice in ["2", "4"]:
            try:
                cmd = [sys.executable, str(self.scripts_dir / "zotero_export.py"), "--export", "csv"]
                subprocess.run(cmd, cwd=str(self.scripts_dir))
                self.print_success(f"CSV export created in metadata/zotero_export.csv")
            except Exception as e:
                self.print_error(f"Could not export to CSV: {e}")

        if choice in ["3", "4"]:
            try:
                cmd = [sys.executable, str(self.scripts_dir / "zotero_export.py"), "--export", "json"]
                subprocess.run(cmd, cwd=str(self.scripts_dir))
                self.print_success(f"JSON export created in metadata/zotero_export.json")
            except Exception as e:
                self.print_error(f"Could not export to JSON: {e}")

        if choice in ["1", "2", "3", "4"]:
            print(f"\n{Colors.CYAN}Next steps:{Colors.ENDC}")
            if choice == "1" or choice == "4":
                print(f"  {Colors.GREEN}★ BibTeX (Recommended):{Colors.ENDC}")
                print(f"    1. Open Zotero")
                print(f"    2. Click File → Import")
                print(f"    3. Select zotero_export.bib from metadata/")
                print()
            if choice == "2" or choice == "4":
                print(f"  CSV:")
                print(f"    1. Open Zotero")
                print(f"    2. Click File → Import")
                print(f"    3. Select zotero_export.csv from metadata/")
                print()

        input(f"\n{Colors.DIM}Press Enter to return to menu...{Colors.ENDC}")

    def menu_manual_overrides(self):
        """Menu option: Manage manual metadata overrides"""
        self.print_section("Manage Manual Metadata & Overrides")

        overrides_file = self.metadata_dir / "manual_metadata_overrides.json"

        print("Options:")
        print(f"  1. View current overrides")
        print(f"  2. Add new override")
        print(f"  3. Edit overrides file")
        print(f"  4. Show articles needing metadata fixes")
        print(f"  0. Back")
        print()

        choice = input(f"{Colors.CYAN}Select option (0-4): {Colors.ENDC}").strip()

        if choice == "0":
            return
        elif choice == "1":
            self._view_overrides()
        elif choice == "2":
            self._add_override()
        elif choice == "3":
            self.print_info(f"Manual overrides file: {overrides_file}")
            print(f"Edit with your preferred text editor and rerun processing.")
        elif choice == "4":
            self._show_articles_needing_fixes()
        else:
            self.print_error("Invalid option")

        input(f"\n{Colors.DIM}Press Enter to return to menu...{Colors.ENDC}")

    def _view_overrides(self):
        """View manual metadata overrides"""
        overrides_file = self.metadata_dir / "manual_metadata_overrides.json"
        if not overrides_file.exists():
            self.print_warning("No manual overrides found")
            return

        try:
            with open(overrides_file, 'r') as f:
                data = json.load(f)
                overrides = data.get('overrides', [])

            print(f"\n{Colors.BOLD}Manual Metadata Overrides:{Colors.ENDC}\n")
            for i, override in enumerate(overrides, 1):
                print(f"{Colors.CYAN}{i}. {override.get('source_file')}{Colors.ENDC}")
                print(f"   Title:  {override.get('title')}")
                print(f"   Author: {override.get('author')}")
                print(f"   Date:   {override.get('date')}")
                print()
        except Exception as e:
            self.print_error(f"Could not read overrides: {e}")

    def _add_override(self):
        """Add a new manual override"""
        print(f"\n{Colors.BOLD}Add Manual Override{Colors.ENDC}\n")

        source_file = input(f"{Colors.CYAN}Source PDF filename: {Colors.ENDC}").strip()
        title = input(f"{Colors.CYAN}Article title: {Colors.ENDC}").strip()
        author = input(f"{Colors.CYAN}Author(s): {Colors.ENDC}").strip()
        date = input(f"{Colors.CYAN}Date (YYYY-MM-DD): {Colors.ENDC}").strip()
        notes = input(f"{Colors.CYAN}Notes: {Colors.ENDC}").strip()

        if not all([source_file, title, date]):
            self.print_error("Title and date are required")
            return

        # Load existing overrides
        overrides_file = self.metadata_dir / "manual_metadata_overrides.json"
        try:
            with open(overrides_file, 'r') as f:
                data = json.load(f)
        except:
            data = {"overrides": []}

        # Add new override
        new_override = {
            "source_file": source_file,
            "title": title,
            "author": author,
            "date": date,
            "notes": notes
        }

        data['overrides'].append(new_override)

        # Save
        try:
            with open(overrides_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.print_success(f"Override added for: {title}")
        except Exception as e:
            self.print_error(f"Could not save override: {e}")

    def _show_articles_needing_fixes(self):
        """Show articles that need manual metadata editing"""
        self._run_query("--needs-editing")

    def menu_rename_pdfs(self):
        """Menu option: Rename PDFs"""
        self.print_section("Rename Archived PDFs")

        self.print_info("Renames PDFs to match markdown filenames (YYYY-MM-DD_Title.pdf)")
        print()

        print("Options:")
        print(f"  1. Rename all PDFs")
        print(f"  2. Preview (dry-run)")
        print(f"  0. Cancel")
        print()

        choice = input(f"{Colors.CYAN}Select option (0-2): {Colors.ENDC}").strip()

        if choice == "1":
            self._run_rename()
        elif choice == "2":
            self._run_rename(dry_run=True)
        elif choice != "0":
            self.print_error("Invalid option")

        input(f"\n{Colors.DIM}Press Enter to return to menu...{Colors.ENDC}")

    def _run_rename(self, dry_run: bool = False):
        """Run PDF renaming"""
        try:
            cmd = [sys.executable, str(self.scripts_dir / "rename_archived_pdfs.py")]
            if dry_run:
                cmd.append("--dry-run")

            print()
            subprocess.run(cmd, cwd=str(self.scripts_dir))
        except Exception as e:
            self.print_error(f"Could not run rename: {e}")

    def menu_list_articles(self):
        """Menu option: List all articles"""
        self.print_section("All Articles (Chronological Order)")
        self._run_query("--list")
        input(f"\n{Colors.DIM}Press Enter to return to menu...{Colors.ENDC}")

    def menu_quick_preview(self):
        """Menu option: Preview article text"""
        self.print_section("Quick Article Preview")

        articles = sorted(list(self.output_dir.glob('*.md')))
        if not articles:
            self.print_warning("No markdown files found")
            input(f"\n{Colors.DIM}Press Enter to return to menu...{Colors.ENDC}")
            return

        print(f"Available articles:\n")
        for i, article in enumerate(articles[:10], 1):
            print(f"  {Colors.CYAN}{i}{Colors.ENDC}. {article.name}")

        if len(articles) > 10:
            print(f"  {Colors.DIM}... and {len(articles) - 10} more{Colors.ENDC}")

        print()
        choice = input(f"{Colors.CYAN}Select article (0 to cancel): {Colors.ENDC}").strip()

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(articles):
                article_file = articles[idx]
                with open(article_file, 'r') as f:
                    content = f.read()

                # Extract title from frontmatter
                lines = content.split('\n')
                title = "Article Text"
                for line in lines[:10]:
                    if line.startswith('title:'):
                        title = line.replace('title:', '').strip()
                        break

                self.print_section(f"Preview: {title}")

                # Show first 1000 chars
                text_start = content.find('---\n', content.find('---') + 3) + 4
                preview = content[text_start:text_start + 1000]
                print(preview)
                print(f"\n{Colors.DIM}... (truncated){Colors.ENDC}")
        except ValueError:
            pass

        input(f"\n{Colors.DIM}Press Enter to return to menu...{Colors.ENDC}")

    def menu_settings(self):
        """Menu option: Settings"""
        self.print_section("System Settings")

        print("System Information:\n")
        print(f"  Base directory:   {self.base_dir}")
        print(f"  Output folder:    {self.output_dir}")
        print(f"  Archive folder:   {self.archive_dir}")
        print(f"  Metadata folder:  {self.metadata_dir}")
        print()

        metadata_file = self.metadata_dir / "articles_metadata.json"
        if metadata_file.exists():
            stat = metadata_file.stat()
            mod_time = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  Last updated:     {mod_time}")

        print()
        input(f"{Colors.DIM}Press Enter to return to menu...{Colors.ENDC}")

    def run(self):
        """Main loop"""
        while True:
            self.show_dashboard()
            self.show_menu()

            choice = input(f"{Colors.CYAN}Select option: {Colors.ENDC}").strip()

            if choice == "1":
                self.menu_process_articles()
            elif choice == "2":
                self.menu_search_articles()
            elif choice == "3":
                self.menu_statistics()
            elif choice == "4":
                self.menu_export_data()
            elif choice == "5":
                self.menu_zotero_export()
            elif choice == "6":
                self.menu_manual_overrides()
            elif choice == "7":
                self.menu_rename_pdfs()
            elif choice == "8":
                self.menu_list_articles()
            elif choice == "9":
                self.menu_quick_preview()
            elif choice == "0":
                self.menu_settings()
            elif choice == "!":
                self.print_header("👋 Thank you for using Article Processing System")
                print(f"{Colors.DIM}Goodbye!{Colors.ENDC}\n")
                break
            else:
                self.print_error("Invalid option. Please try again.")
                input(f"\n{Colors.DIM}Press Enter to continue...{Colors.ENDC}")


def main():
    """Entry point"""
    try:
        cli = ArticleForgeCLi()
        cli.run()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Interrupted by user{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.ENDC}")
        sys.exit(1)


if __name__ == "__main__":
    main()
