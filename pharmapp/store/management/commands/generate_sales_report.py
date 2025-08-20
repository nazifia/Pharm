from django.core.management.base import BaseCommand
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from store.models import DispensingLog, Sales, SalesItem, WholesaleSalesItem, Receipt, WholesaleReceipt, Expense
import csv
import os

class Command(BaseCommand):
    help = 'Generate comprehensive sales reports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--period',
            type=str,
            choices=['daily', 'weekly', 'monthly', 'yearly', 'custom'],
            default='daily',
            help='Report period (default: daily)'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for custom period (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for custom period (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--format',
            type=str,
            choices=['console', 'csv', 'both'],
            default='console',
            help='Output format (default: console)'
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default='reports',
            help='Output directory for CSV files (default: reports)'
        )

    def handle(self, *args, **options):
        period = options['period']
        output_format = options['format']
        output_dir = options['output_dir']
        
        # Calculate date range
        end_date = timezone.now().date()
        
        if period == 'daily':
            start_date = end_date
        elif period == 'weekly':
            start_date = end_date - timedelta(days=7)
        elif period == 'monthly':
            start_date = end_date.replace(day=1)
        elif period == 'yearly':
            start_date = end_date.replace(month=1, day=1)
        elif period == 'custom':
            if not options['start_date'] or not options['end_date']:
                self.stdout.write(
                    self.style.ERROR('Custom period requires --start-date and --end-date')
                )
                return
            start_date = datetime.strptime(options['start_date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(options['end_date'], '%Y-%m-%d').date()
        
        # Generate report
        report_data = self.generate_sales_report(start_date, end_date)
        
        # Output report
        if output_format in ['console', 'both']:
            self.display_console_report(report_data, period, start_date, end_date)
        
        if output_format in ['csv', 'both']:
            self.generate_csv_report(report_data, period, start_date, end_date, output_dir)

    def generate_sales_report(self, start_date, end_date):
        """Generate comprehensive sales report data"""
        
        # Filter dispensing logs for the period
        dispensing_logs = DispensingLog.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        )
        
        # Sales summary
        total_sales = dispensing_logs.filter(status='Dispensed').aggregate(
            total_amount=Sum('amount'),
            total_quantity=Sum('quantity'),
            total_transactions=Count('id')
        )
        
        # Returns summary
        returns = dispensing_logs.filter(status__in=['Returned', 'Partially Returned']).aggregate(
            total_returns=Sum('amount'),
            return_quantity=Sum('quantity'),
            return_transactions=Count('id')
        )
        
        # Net sales
        net_sales = (total_sales['total_amount'] or Decimal('0')) - (returns['total_returns'] or Decimal('0'))
        
        # Top selling items
        top_items = dispensing_logs.filter(status='Dispensed').values('name').annotate(
            total_quantity=Sum('quantity'),
            total_amount=Sum('amount'),
            transaction_count=Count('id')
        ).order_by('-total_amount')[:10]
        
        # Sales by user
        sales_by_user = dispensing_logs.filter(status='Dispensed').values(
            'user__username', 'user__first_name', 'user__last_name'
        ).annotate(
            total_sales=Sum('amount'),
            total_items=Count('id'),
            avg_transaction=Avg('amount')
        ).order_by('-total_sales')
        
        # Daily breakdown
        daily_sales = dispensing_logs.filter(status='Dispensed').extra(
            select={'day': 'date(created_at)'}
        ).values('day').annotate(
            daily_total=Sum('amount'),
            daily_transactions=Count('id')
        ).order_by('day')
        
        # Payment method breakdown - exclude returned receipts
        receipts = Receipt.objects.filter(
            date__date__gte=start_date,
            date__date__lte=end_date,
            is_returned=False  # Exclude returned receipts
        )
        wholesale_receipts = WholesaleReceipt.objects.filter(
            date__date__gte=start_date,
            date__date__lte=end_date,
            is_returned=False  # Exclude returned wholesale receipts
        )

        payment_methods = {}
        for receipt in receipts:
            method = receipt.payment_method
            payment_methods[method] = payment_methods.get(method, Decimal('0')) + receipt.total_amount

        for receipt in wholesale_receipts:
            method = receipt.payment_method
            payment_methods[method] = payment_methods.get(method, Decimal('0')) + receipt.total_amount
        
        # Expenses for the period
        expenses = Expense.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(total_expenses=Sum('amount'))
        
        return {
            'period': {'start': start_date, 'end': end_date},
            'sales_summary': total_sales,
            'returns_summary': returns,
            'net_sales': net_sales,
            'top_items': list(top_items),
            'sales_by_user': list(sales_by_user),
            'daily_sales': list(daily_sales),
            'payment_methods': payment_methods,
            'expenses': expenses['total_expenses'] or Decimal('0'),
            'profit': net_sales - (expenses['total_expenses'] or Decimal('0'))
        }

    def display_console_report(self, data, period, start_date, end_date):
        """Display report in console"""
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS(f"PHARMAPP SALES REPORT - {period.upper()}"))
        self.stdout.write(self.style.SUCCESS(f"Period: {start_date} to {end_date}"))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}\n"))
        
        # Sales Summary
        self.stdout.write(self.style.WARNING("📊 SALES SUMMARY"))
        self.stdout.write(f"Total Sales: ₦{data['sales_summary']['total_amount'] or 0:,.2f}")
        self.stdout.write(f"Total Transactions: {data['sales_summary']['total_transactions'] or 0}")
        self.stdout.write(f"Total Items Sold: {data['sales_summary']['total_quantity'] or 0}")
        self.stdout.write(f"Returns: ₦{data['returns_summary']['total_returns'] or 0:,.2f}")
        self.stdout.write(f"Net Sales: ₦{data['net_sales']:,.2f}")
        self.stdout.write(f"Total Expenses: ₦{data['expenses']:,.2f}")
        self.stdout.write(f"Net Profit: ₦{data['profit']:,.2f}\n")
        
        # Top Items
        self.stdout.write(self.style.WARNING("🏆 TOP SELLING ITEMS"))
        for i, item in enumerate(data['top_items'][:5], 1):
            self.stdout.write(f"{i}. {item['name']}: ₦{item['total_amount']:,.2f} ({item['total_quantity']} units)")
        
        # Top Users
        self.stdout.write(self.style.WARNING("\n👥 TOP PERFORMING STAFF"))
        for i, user in enumerate(data['sales_by_user'][:5], 1):
            name = f"{user['user__first_name']} {user['user__last_name']}" if user['user__first_name'] else user['user__username']
            self.stdout.write(f"{i}. {name}: ₦{user['total_sales']:,.2f} ({user['total_items']} items)")
        
        # Payment Methods
        self.stdout.write(self.style.WARNING("\n💳 PAYMENT METHODS"))
        for method, amount in data['payment_methods'].items():
            self.stdout.write(f"{method}: ₦{amount:,.2f}")
        
        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))

    def generate_csv_report(self, data, period, start_date, end_date, output_dir):
        """Generate CSV report files"""
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Sales summary CSV
        summary_file = os.path.join(output_dir, f'sales_summary_{period}_{timestamp}.csv')
        with open(summary_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Metric', 'Value'])
            writer.writerow(['Period Start', start_date])
            writer.writerow(['Period End', end_date])
            writer.writerow(['Total Sales', f"₦{data['sales_summary']['total_amount'] or 0:,.2f}"])
            writer.writerow(['Total Transactions', data['sales_summary']['total_transactions'] or 0])
            writer.writerow(['Total Items Sold', data['sales_summary']['total_quantity'] or 0])
            writer.writerow(['Returns', f"₦{data['returns_summary']['total_returns'] or 0:,.2f}"])
            writer.writerow(['Net Sales', f"₦{data['net_sales']:,.2f}"])
            writer.writerow(['Total Expenses', f"₦{data['expenses']:,.2f}"])
            writer.writerow(['Net Profit', f"₦{data['profit']:,.2f}"])
        
        # Top items CSV
        items_file = os.path.join(output_dir, f'top_items_{period}_{timestamp}.csv')
        with open(items_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Rank', 'Item Name', 'Total Amount', 'Quantity Sold', 'Transactions'])
            for i, item in enumerate(data['top_items'], 1):
                writer.writerow([
                    i, item['name'], f"₦{item['total_amount']:,.2f}",
                    item['total_quantity'], item['transaction_count']
                ])
        
        # Staff performance CSV
        staff_file = os.path.join(output_dir, f'staff_performance_{period}_{timestamp}.csv')
        with open(staff_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Rank', 'Staff Name', 'Total Sales', 'Items Sold', 'Avg Transaction'])
            for i, user in enumerate(data['sales_by_user'], 1):
                name = f"{user['user__first_name']} {user['user__last_name']}" if user['user__first_name'] else user['user__username']
                writer.writerow([
                    i, name, f"₦{user['total_sales']:,.2f}",
                    user['total_items'], f"₦{user['avg_transaction'] or 0:,.2f}"
                ])
        
        self.stdout.write(
            self.style.SUCCESS(f"\nCSV reports generated in '{output_dir}' directory:")
        )
        self.stdout.write(f"- {summary_file}")
        self.stdout.write(f"- {items_file}")
        self.stdout.write(f"- {staff_file}")
