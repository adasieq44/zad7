from src.models import Apartment, Bill, Parameters, Tenant, TenantSettlement, Transfer, ApartmentSettlement, BlacklistedTenant
from typing import List, Tuple
from datetime import datetime

class Manager:
    def __init__(self, parameters: Parameters):
        self.parameters = parameters 

        self.apartments = {}
        self.tenants = {}
        self.transfers = []
        self.bills = []
        self.blacklisted_tenants = {}
       
        self.load_data()

    def load_data(self):
        self.apartments = Apartment.from_json_file(self.parameters.apartments_json_path)
        self.tenants = Tenant.from_json_file(self.parameters.tenants_json_path)
        self.transfers = Transfer.from_json_file(self.parameters.transfers_json_path)
        self.bills = Bill.from_json_file(self.parameters.bills_json_path)
        self.blacklisted_tenants = BlacklistedTenant.from_json_file(self.parameters.blacklisted_tenants_json_path)

    def check_tenants_apartment_keys(self) -> bool:
        for tenant in self.tenants.values():
            if tenant.apartment not in self.apartments:
                return False
        return True
    
    def get_apartment(self, apartment_key: str) -> Apartment | None:
        return self.apartments.get(apartment_key, None)

    def is_tenant_blacklisted(self, tenant_name: str) -> bool:
        return any(blacklisted.name == tenant_name for blacklisted in self.blacklisted_tenants.values())

    def get_transfer_errors(self) -> List[dict]:
        """Return list of transfer errors. Each item is a dict with keys: index, transfer, errors.

        Errors detected:
        - 'unassigned_tenant': transfer.tenant not present in `self.tenants`
        - 'settlement_outside_agreement': transfer settlement year/month outside tenant agreement range
        - 'tenant_dates_parse_error': tenant agreement dates could not be parsed
        """
        errors = []
        for idx, transfer in enumerate(self.transfers):
            transfer_errors: List[str] = []

            if transfer.tenant not in self.tenants:
                transfer_errors.append('unassigned_tenant')
            else:
                tenant = self.tenants[transfer.tenant]
                if transfer.settlement_year is not None and transfer.settlement_month is not None:
                    try:
                        start = datetime.strptime(tenant.date_agreement_from, "%Y-%m-%d")
                        end = datetime.strptime(tenant.date_agreement_to, "%Y-%m-%d")
                        trans_dt = datetime(transfer.settlement_year, transfer.settlement_month, 1)
                        if trans_dt < start or trans_dt > end:
                            transfer_errors.append('settlement_outside_agreement')
                    except Exception:
                        transfer_errors.append('tenant_dates_parse_error')

            if transfer_errors:
                errors.append({
                    'index': idx,
                    'transfer': transfer,
                    'errors': transfer_errors
                })

        return errors

    def has_transfer_errors(self) -> bool:
        """Convenience method: True if any transfer errors detected."""
        return len(self.get_transfer_errors()) > 0

    def get_apartment_costs(self, apartment_key: str, year: int = None, month: int = None) -> float | None:
        if month is not None and (month < 1 or month > 12):
            raise ValueError("Month must be between 1 and 12")
        if apartment_key not in self.apartments:
            return None
        total_cost = 0.0
        for bill in self.bills:
            if bill.apartment == apartment_key and (year is None or bill.settlement_year == year) and (month is None or bill.settlement_month == month):
                total_cost += bill.amount_pln
        return total_cost

    def get_settlement(self, apartment_key: str, year: int, month: int) -> ApartmentSettlement | None:
        if month < 1 or month > 12:
            raise ValueError("Month must be between 1 and 12")
        if apartment_key not in self.apartments:
            return None
        total_cost = self.get_apartment_costs(apartment_key, year, month)
        if total_cost is None:
            return None
        
        return ApartmentSettlement(
            key=f"{apartment_key}-{year}-{month}",
            apartment=apartment_key,
            year=year,
            month=month,
            total_due_pln=total_cost
        )
    
    def create_tenants_settlements(self, apartment_settlement: ApartmentSettlement) -> List[TenantSettlement] | None:
        if apartment_settlement.month < 1 or apartment_settlement.month > 12:
            raise ValueError("Month must be between 1 and 12")
        if apartment_settlement.apartment not in self.apartments:
            return None
        tenants_in_apartment = [tenant for tenant in self.tenants.values() if tenant.apartment == apartment_settlement.apartment]
        if not tenants_in_apartment:
            return []
        
        return [
            TenantSettlement(
                tenant=tenant.name,
                apartment_settlement=apartment_settlement.key,
                month=apartment_settlement.month,
                year=apartment_settlement.year,
                total_due_pln=apartment_settlement.total_due_pln / len(tenants_in_apartment)
            )
        for tenant in tenants_in_apartment ] 
    
    def get_debtors(self, apartment_key: str, year: int, month: int) -> List[str]:
        if month < 1 or month > 12:
            raise ValueError("Month must be between 1 and 12")
        output = []
        settlement = self.get_settlement(apartment_key, year, month)
        tenant_settlements = self.create_tenants_settlements(settlement)

        for tenant_settlement in tenant_settlements:
            tenant_transfers = [transfer for transfer in self.transfers if self.tenants[transfer.tenant].name == tenant_settlement.tenant and transfer.settlement_year == year and transfer.settlement_month == month]
            total_paid = sum([transfer.amount_pln for transfer in tenant_transfers if transfer.settlement_year == year and transfer.settlement_month == month])
            if total_paid < tenant_settlement.total_due_pln:
                output.append(tenant_settlement.tenant)
        return output
    
    def calculate_tax(self, year: int, month: int, tax_rate: float) -> float:
        total_income = sum([transfer.amount_pln for transfer in self.transfers if transfer.settlement_year == year and transfer.settlement_month == month])
        return round(total_income * tax_rate, 0)
    
    def check_deposits(self) -> float:
        total_deposits = 0.0
        total_due = 0.0
        for tenant_key, tenant in self.tenants.items():
            total_deposits += sum([transfer.amount_pln for transfer in self.transfers if self.tenants[transfer.tenant].name == tenant.name and transfer.type == 'deposit'])
            total_due += tenant.deposit_pln
        
        return total_deposits - total_due
    
    def get_annual_balance(self, year: int) -> float:
        total_income = sum([transfer.amount_pln for transfer in self.transfers if transfer.settlement_year == year])
        total_due = sum([bill.amount_pln for bill in self.bills if bill.settlement_year == year])
        return total_income - total_due
    
    def has_any_bills(self, apartment_key: str, year: int, month: int) -> bool:
        if month < 1 or month > 12:
            raise ValueError("Month must be between 1 and 12")
        if apartment_key not in self.apartments:
            raise ValueError("Apartment key does not exist")
        return any([bill for bill in self.bills if bill.apartment == apartment_key and bill.settlement_year == year and bill.settlement_month == month])