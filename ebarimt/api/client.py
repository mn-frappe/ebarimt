# Copyright (c) 2024, Digital Consulting Service LLC (Mongolia)
# License: GNU General Public License v3
"""
eBarimt API Client - Unified client for all eBarimt services
Supports POS API, Public API, Easy Register, and OAT APIs
"""

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime, getdate
import requests
import json
from urllib.parse import urljoin
from ebarimt.api.auth import ITCAuth


class EBarimtClient:
	"""
	Unified eBarimt API Client
	
	Handles all eBarimt API interactions with automatic fallback:
	1. api.frappe.mn (primary proxy)
	2. IP fallback (103.153.141.167)
	3. Direct government URLs
	"""
	
	def __init__(self, settings=None):
		"""Initialize client with settings"""
		self.settings = settings or frappe.get_cached_doc("eBarimt Settings")
		self.auth = ITCAuth(self.settings)
		self._setup_urls()
	
	def _setup_urls(self):
		"""Setup all API URLs based on environment"""
		is_staging = self.settings.environment == "Staging"
		
		# Primary URLs (via api.frappe.mn proxy)
		self.proxy_base = "https://api.frappe.mn"
		self.ip_fallback = "http://103.153.141.167"
		
		if is_staging:
			# POS API (local terminal simulation)
			self.pos_url = f"{self.proxy_base}/test/rest"
			self.pos_url_ip = f"{self.ip_fallback}/test/rest"
			
			# Public API (ebarimt.mn)
			self.api_url = f"{self.proxy_base}/ebarimt-staging"
			self.api_url_direct = "https://st-api.ebarimt.mn"
			
			# ITC Service (OAT, Easy Register)
			self.itc_url = f"{self.proxy_base}/itc-service-staging"
			self.itc_url_direct = "https://st-service.itc.gov.mn"
		else:
			# Production URLs
			self.pos_url = f"{self.proxy_base}/rest"
			self.pos_url_ip = f"{self.ip_fallback}/rest"
			
			self.api_url = f"{self.proxy_base}/ebarimt-prod"
			self.api_url_direct = "https://api.ebarimt.mn"
			
			self.itc_url = f"{self.proxy_base}/itc-service-prod"
			self.itc_url_direct = "https://service.itc.gov.mn"
	
	def _request(self, method, url, fallback_urls=None, auth_required=False, 
				 api_key=None, **kwargs):
		"""
		Make HTTP request with automatic fallback
		
		Args:
			method: HTTP method (GET, POST, DELETE)
			url: Primary URL
			fallback_urls: List of fallback URLs to try
			auth_required: Whether to include Bearer token
			api_key: X-API-KEY header value if needed
			**kwargs: Additional requests parameters
		"""
		headers = kwargs.pop("headers", {})
		
		# Add auth header if required
		if auth_required:
			headers.update(self.auth.get_auth_header())
		
		# Add API key if provided
		if api_key:
			headers["X-API-KEY"] = api_key
		
		# Default headers
		if "Content-Type" not in headers and method.upper() in ("POST", "PUT"):
			headers["Content-Type"] = "application/json"
		
		kwargs["headers"] = headers
		kwargs.setdefault("timeout", 30)
		kwargs.setdefault("verify", True)
		
		# URLs to try
		urls = [url] + (fallback_urls or [])
		
		last_error = None
		for try_url in urls:
			try:
				response = requests.request(method, try_url, **kwargs)
				
				# Log request
				self._log_request(method, try_url, response.status_code, kwargs.get("json"))
				
				return response
				
			except requests.exceptions.Timeout:
				last_error = f"Timeout: {try_url}"
				continue
			except requests.exceptions.ConnectionError:
				last_error = f"Connection failed: {try_url}"
				continue
			except Exception as e:
				last_error = f"{try_url}: {str(e)}"
				continue
		
		# All URLs failed
		frappe.throw(_("eBarimt API connection failed. {0}").format(last_error))
	
	def _log_request(self, method, url, status_code, payload=None):
		"""Log API request for debugging"""
		if self.settings.enable_debug_log:
			frappe.logger("ebarimt").info(
				f"{method} {url} -> {status_code}"
			)
	
	# =========================================================================
	# POS API - Receipt Management (Local Terminal)
	# =========================================================================
	
	def get_info(self):
		"""
		Get POS terminal information
		Returns operator, merchants, lottery count, etc.
		"""
		response = self._request(
			"GET",
			f"{self.pos_url}/info",
			fallback_urls=[f"{self.pos_url_ip}/info"]
		)
		
		if response.status_code == 200:
			return response.json()
		elif response.status_code == 503:
			frappe.throw(_("POS API is not configured. Please register merchants first."))
		else:
			frappe.throw(_("Failed to get POS info: {0}").format(response.text))
	
	def create_receipt(self, receipt_data):
		"""
		Create a new VAT receipt
		
		Args:
			receipt_data: Dict with receipt details:
				- amount: Total amount
				- vat: VAT amount
				- cashAmount: Cash payment
				- nonCashAmount: Non-cash payment
				- cityTax: City tax amount
				- districtCode: District code (4 digits)
				- posNo: POS number
				- customerTin: Customer TIN (for B2B)
				- billType: Receipt type (B2B_RECEIPT or B2C_RECEIPT)
				- returnBillId: Original receipt ID (for returns)
				- stocks: List of items
				- payments: List of payments
		
		Returns:
			dict: Receipt response with lottery number, QR, etc.
		"""
		response = self._request(
			"POST",
			f"{self.pos_url}/receipt",
			fallback_urls=[f"{self.pos_url_ip}/receipt"],
			json=receipt_data
		)
		
		if response.status_code == 200:
			return response.json()
		else:
			error_data = response.json() if response.text else {}
			error_msg = error_data.get("message", response.text)
			frappe.throw(_("Failed to create receipt: {0}").format(error_msg))
	
	def get_receipt_info(self, receipt_id):
		"""
		Get receipt information by ID
		
		Args:
			receipt_id: 33-digit receipt ID (DDTD)
			
		Returns:
			dict: Receipt information
		"""
		response = self._request(
			"GET",
			f"{self.pos_url}/receipt/{receipt_id}",
			fallback_urls=[f"{self.pos_url_ip}/receipt/{receipt_id}"]
		)
		
		if response.status_code == 200:
			return response.json()
		return None
	
	def void_receipt(self, receipt_id, receipt_date=None):
		"""
		Void/return a B2C receipt (alias for delete_receipt)
		Only works for unconfirmed B2C receipts
		
		Args:
			receipt_id: 33-digit receipt ID (DDTD)
			receipt_date: Receipt date (yyyy-MM-dd HH:mm:ss), defaults to now
		"""
		if not receipt_date:
			from frappe.utils import now_datetime
			receipt_date = now_datetime().strftime("%Y-%m-%d %H:%M:%S")
		
		return self.delete_receipt(receipt_id, receipt_date)
	
	def delete_receipt(self, receipt_id, receipt_date):
		"""
		Void/return a B2C receipt
		Only works for unconfirmed B2C receipts
		
		Args:
			receipt_id: 33-digit receipt ID (DDTD)
			receipt_date: Receipt date (yyyy-MM-dd HH:mm:ss)
		"""
		response = self._request(
			"DELETE",
			f"{self.pos_url}/receipt",
			fallback_urls=[f"{self.pos_url_ip}/receipt"],
			json={
				"id": receipt_id,
				"date": receipt_date
			}
		)
		
		if response.status_code == 200:
			return response.json()
		else:
			frappe.throw(_("Failed to void receipt: {0}").format(response.text))
	
	def send_data(self):
		"""
		Sync receipts with central eBarimt system
		Usually called automatically by POS API
		"""
		response = self._request(
			"GET",
			f"{self.pos_url}/sendData",
			fallback_urls=[f"{self.pos_url_ip}/sendData"]
		)
		return response.json() if response.status_code == 200 else {}
	
	def get_bank_accounts(self, tin=None):
		"""
		Get registered bank accounts for merchant
		
		Args:
			tin: Taxpayer TIN (optional, defaults to current merchant)
		"""
		params = {"tin": tin} if tin else {}
		response = self._request(
			"GET",
			f"{self.pos_url}/bankAccounts",
			fallback_urls=[f"{self.pos_url_ip}/bankAccounts"],
			params=params
		)
		
		if response.status_code == 200:
			return response.json()
		return []
	
	# =========================================================================
	# Public API - Taxpayer & Product Lookup
	# =========================================================================
	
	def get_taxpayer_info(self, tin):
		"""
		Get taxpayer information by TIN
		
		Args:
			tin: Taxpayer Identification Number
			
		Returns:
			dict: Taxpayer info (name, vatPayer, cityPayer, etc.)
		"""
		response = self._request(
			"GET",
			f"{self.api_url}/api/info/check/getInfo",
			fallback_urls=[f"{self.api_url_direct}/api/info/check/getInfo"],
			params={"tin": tin}
		)
		
		if response.status_code == 200:
			data = response.json()
			if data.get("status") == 200:
				return data.get("data", {})
		
		return None
	
	def get_tin_by_regno(self, reg_no):
		"""
		Get TIN from registration number
		
		Args:
			reg_no: Registration number (company or personal)
			
		Returns:
			str: TIN number
		"""
		response = self._request(
			"GET",
			f"{self.api_url}/api/info/check/getTinInfo",
			fallback_urls=[f"{self.api_url_direct}/api/info/check/getTinInfo"],
			params={"regNo": reg_no}
		)
		
		if response.status_code == 200:
			data = response.json()
			if data.get("status") == 200:
				return str(data.get("data", ""))
		
		return None
	
	def get_district_codes(self):
		"""
		Get all district/branch codes
		
		Returns:
			list: District codes with names
		"""
		response = self._request(
			"GET",
			f"{self.api_url}/api/info/check/getBranchInfo",
			fallback_urls=[f"{self.api_url_direct}/api/info/check/getBranchInfo"]
		)
		
		if response.status_code == 200:
			data = response.json()
			if data.get("status") == 200:
				return data.get("data", [])
		
		return []
	
	def get_tax_codes(self):
		"""
		Get VAT exempt/zero-rate product codes
		
		Returns:
			list: Tax product codes with validity dates
		"""
		response = self._request(
			"GET",
			f"{self.api_url}/api/receipt/receipt/getProductTaxCode",
			fallback_urls=[f"{self.api_url_direct}/api/receipt/receipt/getProductTaxCode"]
		)
		
		if response.status_code == 200:
			data = response.json()
			if data.get("status") == 200:
				return data.get("data", [])
		
		return []
	
	def lookup_barcode(self, *levels):
		"""
		Lookup BUNA classification or barcode
		Hierarchical: Sector > SubSector > Group > Class > SubClass > BUNA > Barcode
		
		Args:
			*levels: Classification codes at each level (0 to 6 params)
			
		Returns:
			list: Child items at next level
		"""
		# Build path based on levels provided
		path_parts = ["api/info/check/barcode/v2"]
		for level in levels:
			path_parts.append(str(level))
		
		path = "/".join(path_parts)
		
		response = self._request(
			"GET",
			f"{self.api_url}/{path}",
			fallback_urls=[f"{self.api_url_direct}/{path}"]
		)
		
		if response.status_code == 200:
			return response.json()
		return []
	
	# =========================================================================
	# Easy Register API - Consumer Lottery
	# =========================================================================
	
	def lookup_consumer_by_regno(self, reg_no):
		"""
		Lookup consumer by registration number or civil ID
		
		Args:
			reg_no: Registration number or Civil ID
			
		Returns:
			dict: Consumer info (loginName, givenName, etc.)
		"""
		response = self._request(
			"GET",
			f"{self.itc_url}/api/easy-register/api/info/consumer/{reg_no}",
			fallback_urls=[f"{self.itc_url_direct}/api/easy-register/api/info/consumer/{reg_no}"],
			auth_required=True
		)
		
		if response.status_code == 200:
			return response.json()
		return None
	
	def lookup_consumer_by_phone(self, phone):
		"""
		Lookup consumer by phone number
		
		Args:
			phone: Phone number
			
		Returns:
			dict: Consumer info with loginName
		"""
		response = self._request(
			"POST",
			f"{self.itc_url}/api/easy-register/rest/v1/getProfile",
			fallback_urls=[f"{self.itc_url_direct}/api/easy-register/rest/v1/getProfile"],
			auth_required=True,
			json={"phoneNum": phone}
		)
		
		if response.status_code == 200:
			data = response.json()
			if data.get("status") == 200:
				return data
		return None
	
	def approve_receipt_qr(self, customer_no, qr_data):
		"""
		Approve receipt for consumer lottery
		
		Args:
			customer_no: 8-9 digit eBarimt customer code
			qr_data: Receipt QR code data
			
		Returns:
			dict: Approval result
		"""
		response = self._request(
			"POST",
			f"{self.itc_url}/api/easy-register/rest/v1/approveQr",
			fallback_urls=[f"{self.itc_url_direct}/api/easy-register/rest/v1/approveQr"],
			auth_required=True,
			json={
				"customerNo": customer_no,
				"qrData": qr_data
			}
		)
		
		if response.status_code == 200:
			return response.json()
		return {"status": response.status_code, "msg": response.text}
	
	def confirm_return_receipt(self, pos_rno=None, lottery_number=None, api_key=None):
		"""
		Confirm return receipt for easy-registered receipts
		
		Args:
			pos_rno: Receipt ID (DDTD)
			lottery_number: Lottery number (alternative to pos_rno)
			api_key: X-API-KEY from ITC
		"""
		payload = {}
		if pos_rno:
			payload["posRno"] = pos_rno
		elif lottery_number:
			payload["lotteryNumber"] = lottery_number
		
		response = self._request(
			"POST",
			f"{self.itc_url}/api/easy-register/rest/v1/setReturnReceipt",
			fallback_urls=[f"{self.itc_url_direct}/api/easy-register/rest/v1/setReturnReceipt"],
			auth_required=True,
			api_key=api_key or self.settings.get_password("api_key"),
			json=payload
		)
		
		if response.status_code == 200:
			return response.json()
		return {"status": response.status_code, "msg": response.text}
	
	# =========================================================================
	# Foreign Tourist API - VAT Refund for Tourists
	# =========================================================================
	
	def get_foreigner_info(self, passport_no=None, f_register=None):
		"""
		Lookup foreign tourist by passport or F-register number
		
		Args:
			passport_no: Foreign passport number
			f_register: F-register number (Mongolian resident foreigner)
			
		Returns:
			dict: Tourist info with customerNo for receipt registration
		"""
		payload = {}
		if passport_no:
			payload["passportNo"] = passport_no
		elif f_register:
			payload["fRegister"] = f_register
		
		response = self._request(
			"POST",
			f"{self.itc_url}/api/easy-register/rest/v1/getForeignerInfo",
			fallback_urls=[f"{self.itc_url_direct}/api/easy-register/rest/v1/getForeignerInfo"],
			auth_required=True,
			json=payload
		)
		
		if response.status_code == 200:
			data = response.json()
			if data.get("status") == 200:
				return data
		return None
	
	def get_foreigner_by_username(self, username):
		"""
		Lookup foreign tourist by eBarimt username
		
		Args:
			username: eBarimt login username
			
		Returns:
			dict: Tourist profile info
		"""
		response = self._request(
			"POST",
			f"{self.itc_url}/api/easy-register/rest/v1/getForeignerByUsername",
			fallback_urls=[f"{self.itc_url_direct}/api/easy-register/rest/v1/getForeignerByUsername"],
			auth_required=True,
			json={"username": username}
		)
		
		if response.status_code == 200:
			data = response.json()
			if data.get("status") == 200:
				return data
		return None
	
	def register_foreigner(self, passport_no, first_name, last_name, country_code, 
						   email=None, phone=None):
		"""
		Register foreign tourist in eBarimt system for VAT refund
		
		Args:
			passport_no: Foreign passport number
			first_name: Tourist first name
			last_name: Tourist last name
			country_code: ISO country code (e.g., 'US', 'CN', 'KR')
			email: Email address (optional)
			phone: Phone number (optional)
			
		Returns:
			dict: Registration result with customerNo
		"""
		payload = {
			"passportNo": passport_no,
			"firstName": first_name,
			"lastName": last_name,
			"countryCode": country_code
		}
		
		if email:
			payload["email"] = email
		if phone:
			payload["phoneNum"] = phone
		
		response = self._request(
			"POST",
			f"{self.itc_url}/api/easy-register/rest/v1/setForeignerInfo",
			fallback_urls=[f"{self.itc_url_direct}/api/easy-register/rest/v1/setForeignerInfo"],
			auth_required=True,
			json=payload
		)
		
		if response.status_code == 200:
			return response.json()
		return {"status": response.status_code, "msg": response.text}
	
	# =========================================================================
	# OAT API - Excise Tax Stamp Tracking
	# =========================================================================
	
	def get_oat_product_info(self, barcode):
		"""
		Get excise tax product information by barcode
		
		Args:
			barcode: Product barcode
			
		Returns:
			dict: Product info (name, category, alcohol %, etc.)
		"""
		response = self._request(
			"GET",
			f"{self.itc_url}/rest/tpiMain/mainApi/getInventoryList",
			fallback_urls=[f"{self.itc_url_direct}/rest/tpiMain/mainApi/getInventoryList"],
			params={"barcode": barcode}
		)
		
		if response.status_code == 200:
			return response.json()
		return None
	
	def get_oat_stock_by_qr(self, qr_code):
		"""
		Get excise stamp info by QR code
		
		Args:
			qr_code: Stamp QR code
		"""
		# This endpoint is on service.itc.gov.mn
		itc_service = f"{self.proxy_base}/itc-service-staging" if self.settings.environment == "Staging" else f"{self.proxy_base}/itc-service-prod"
		
		response = self._request(
			"GET",
			f"{itc_service}/api/inventory/stock/getStockQr",
			params={"stockQr": qr_code},
			auth_required=True
		)
		
		if response.status_code == 200:
			return response.json()
		return None
	
	def get_available_stamps(self, reg_no, barcode, stock_type, position_id, year, month):
		"""
		Get available excise stamps for sale
		
		Args:
			reg_no: Seller registration number
			barcode: Product barcode
			stock_type: Product type code (4-33)
			position_id: Stamp type code (3-6)
			year: Year
			month: Month
			
		Returns:
			list: Available stamp numbers
		"""
		response = self._request(
			"GET",
			f"{self.itc_url}/api/inventory/getActiveStockNoPos",
			fallback_urls=[f"{self.itc_url_direct}/api/inventory/getActiveStockNoPos"],
			auth_required=True,
			params={
				"regNo": reg_no,
				"barCode": barcode,
				"stockType": stock_type,
				"positionId": position_id,
				"year": year,
				"month": month
			}
		)
		
		if response.status_code == 200:
			data = response.json()
			if data.get("status") == 200:
				return data.get("data", [])
		return []
	
	def record_stamp_sale(self, pos_rno, merchant_regno, customer_no, date, stocks):
		"""
		Record excise stamp sale transaction
		
		Args:
			pos_rno: Receipt ID
			merchant_regno: Seller registration number
			customer_no: Buyer registration number
			date: Transaction date
			stocks: List of stamp details [{barCode, stockType, positionNo, stockNo: [...]}]
		"""
		response = self._request(
			"POST",
			f"{self.itc_url}/api/inventory/posSetTransaction",
			fallback_urls=[f"{self.itc_url_direct}/api/inventory/posSetTransaction"],
			auth_required=True,
			json={
				"posRno": pos_rno,
				"mrchRegno": merchant_regno,
				"customerNo": customer_no,
				"date": date,
				"stocks": stocks
			}
		)
		
		if response.status_code == 200:
			return response.json()
		return {"status": response.status_code, "msg": response.text}
	
	def create_oat_receipt(self, receipt_data):
		"""
		Create OAT receipt for breakage/spoilage/promotion
		
		Args:
			receipt_data: Dict with:
				- totalAmount
				- merchantTin
				- customerTin
				- tranType: 1=Raw materials, 2=Promotion, 3=Breakage
				- receiptType: 1=Spirit, 2=Sales
				- details: [{barCode, qty, unitPrice, positionNo, stock: [...]}]
		"""
		response = self._request(
			"POST",
			f"{self.itc_url}/api/inventory/createReceiptApi",
			fallback_urls=[f"{self.itc_url_direct}/api/inventory/createReceiptApi"],
			auth_required=True,
			json=receipt_data
		)
		
		if response.status_code == 200:
			return response.json()
		return {"status": response.status_code, "msg": response.text}
	
	def get_available_stamps_paginated(self, reg_no, barcode, stock_type, position_id, 
									   page_number=1, page_size=100, api_key=None):
		"""
		Get available excise stamps with pagination and detailed info
		Returns manufacturer info, QR codes, etc.
		
		Args:
			reg_no: Seller registration number
			barcode: Product barcode
			stock_type: Product type code (4-33)
			position_id: Stamp type code (3-6)
			page_number: Page number for pagination
			page_size: Items per page (max 100)
			api_key: X-API-KEY header (optional)
			
		Returns:
			list: Detailed stamp info [{barCode, orderDate, manufactorRegno, productName, qrCode, stockNumber}]
		"""
		headers = {}
		if api_key:
			headers["X-API-KEY"] = api_key
		
		response = self._request(
			"GET",
			f"{self.itc_url}/api/inventory/getActiveStockInfo",
			fallback_urls=[f"{self.itc_url_direct}/api/inventory/getActiveStockInfo"],
			auth_required=True,
			headers=headers,
			params={
				"regNo": reg_no,
				"barCode": barcode,
				"stockType": stock_type,
				"positionId": position_id,
				"pageNumber": page_number,
				"pageSize": page_size
			}
		)
		
		if response.status_code == 200:
			data = response.json()
			if data.get("status") == 200:
				return data.get("data", [])
		return []
	
	def set_product_owner(self, pos_rno, products):
		"""
		Mark products as own-manufactured for multi-manufacturer scenarios
		
		Args:
			pos_rno: Receipt ID (33-digit DDTD)
			products: List of [{barcode, isProductOwner (1=own, 0=other)}]
			
		Returns:
			dict: Result with status
		"""
		response = self._request(
			"POST",
			f"{self.api_url}/api/tpi/receipt/setPosReceiptDtlByProductOwner",
			fallback_urls=[f"{self.api_url_direct}/api/tpi/receipt/setPosReceiptDtlByProductOwner"],
			auth_required=True,
			json={
				"posRno": pos_rno,
				"productOwnerDtlModelList": products
			}
		)
		
		if response.status_code == 200:
			return response.json()
		return {"status": response.status_code, "msg": response.text}
	
	# =========================================================================
	# TPI Data API - Sales Data (Night-time only 1:00-7:00)
	# =========================================================================
	
	def get_sales_data(self, tin, start_date, end_date):
		"""
		Get sales breakdown data (available 1:00-7:00 AM only)
		"""
		response = self._request(
			"POST",
			f"{self.api_url}/api/tpi/receipt/getSalesTotalData",
			fallback_urls=[f"{self.api_url_direct}/api/tpi/receipt/getSalesTotalData"],
			auth_required=True,
			api_key=self.settings.get_password("api_key"),
			json={
				"tin": tin,
				"startDate": start_date,
				"endDate": end_date
			}
		)
		
		if response.status_code == 200:
			return response.json()
		return {"status": response.status_code, "msg": response.text}
	
	# =========================================================================
	# Operator API
	# =========================================================================
	
	def register_merchant(self, pos_no, merchant_tins, api_key=None):
		"""
		Register merchants to operator POS
		
		Args:
			pos_no: POS number
			merchant_tins: List of merchant TINs to register
			api_key: X-API-KEY from ITC
		"""
		response = self._request(
			"POST",
			f"{self.api_url}/api/tpi/receipt/saveOprMerchants",
			fallback_urls=[f"{self.api_url_direct}/api/tpi/receipt/saveOprMerchants"],
			auth_required=True,
			api_key=api_key or self.settings.get_password("api_key"),
			json={
				"posNo": pos_no,
				"merchantTins": merchant_tins
			}
		)
		
		if response.status_code == 200:
			return response.json()
		return {"status": response.status_code, "msg": response.text}


# Convenience function
def get_client():
	"""Get EBarimtClient instance with current settings"""
	return EBarimtClient()
