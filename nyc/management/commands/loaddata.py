from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime, parse_date
from nyc.models import Person, Bill, Organization, Action, Post, Membership
import requests
import json
import pytz

ocd_jurisdiction_id = 'ocd-jurisdiction/country:us/state:ny/place:new_york/government'
ocd_city_council_id = 'ocd-organization/389257d3-aefe-42df-b3a2-a0d56d0ea731'
base_url = 'http://api.opencivicdata.org'
eastern = pytz.timezone('US/Eastern')


class Command(BaseCommand):
	help = 'loads in data from the open civic data API'

	def add_arguments(self, parser):
		parser.add_argument('--endpoint', help="a specific endpoint to load data from")

	def handle(self, *args, **options):

		if options['endpoint'] == 'organizations':
			print "\nLOADING ORGANIZATIONS\n"
			self.grab_organizations()
			print "\ndone!"
		elif options['endpoint'] == 'bills':
			print "\nLOADING BILLS\n"
			self.grab_bills()
			print "\ndone!"
		elif options['endpoint'] == 'people':
			print "\nLOADING PEOPLE\n"
			self.grab_people()
			print "\ndone!"
		else:
			print "\nLOADING EVERYTHING\n"
			self.grab_organizations()
			self.grab_bills()
			self.grab_people()
			print "\ndone!"


	def grab_organizations(self):
		# this grabs all organizations within a jurisdiction
		org_url = base_url+'/organizations/?jurisdiction_id='+ocd_jurisdiction_id
		r = requests.get(org_url)
		page_json = json.loads(r.text)

		for i in range(page_json['meta']['max_page']):

			r = requests.get(org_url+'&page='+str(i+1))
			page_json = json.loads(r.text)

			for result in page_json['results']:
				obj, created = Organization.objects.get_or_create(
						ocd_id=result['id'],
						name=result['name'],
						classification=result['classification']
					)

				if created:
					print '   adding %s' % result['id'] 

				self.grab_posts(obj)

	def grab_posts(self, organization):
		# loads posts for a given organization

		url = base_url+'/'+organization.ocd_id
		r = requests.get(url)
		page_json = json.loads(r.text)

		for post_json in page_json['posts']:

			obj, created = Post.objects.get_or_create(
					ocd_id = post_json['id'],
					label = post_json['label'],
					role = post_json['role'],
					organization = organization
				)

			if created:
				print '      adding post: %s %s' %(post_json['role'], post_json['label'])

	def grab_people(self):
		# find people associated with existing organizations

		orgs = Organization.objects.all()

		for organization in orgs:
			url = base_url+'/'+organization.ocd_id
			r = requests.get(url)
			page_json = json.loads(r.text)

			for membership_json in page_json['memberships']:

				self.grab_person_memberships(membership_json['person']['id'])



	def grab_bills(self):
		# this grabs all bills & associated actions from city council
		# organizations need to be populated before bills & actions are populated
		bill_url = base_url+'/bills/?from_organization_id='+ocd_city_council_id
		r = requests.get(bill_url)
		page_json = json.loads(r.text)

		for i in range(page_json['meta']['max_page']):

			r = requests.get(bill_url+'&page='+str(i+1))
			page_json = json.loads(r.text)

			for result in page_json['results']:
				self.grab_bill(result['id'])

	def grab_bill(self, bill_id):

		bill_url = base_url+'/'+bill_id
		r = requests.get(bill_url)
		page_json = json.loads(r.text)

		from_org = Organization.objects.filter(ocd_id=page_json['from_organization']['id']).first()

		obj, created = Bill.objects.get_or_create(
				ocd_id=bill_id,
				name=page_json['title'],
				classification=page_json['classification'],
				date_created=page_json['created_at'],
				date_updated=page_json['updated_at'],
				source_url=page_json['sources'][0]['url'],
				source_note=page_json['sources'][0]['note'],
				from_organization=from_org
			)

		if created:
			print '   adding %s' % bill_id
		else:
			print '   already exists'


		for action_json in page_json['actions']:
			self.load_action(action_json, obj)

	def load_action(self, action_json, bill):

		org = Organization.objects.filter(ocd_id=action_json['organization']['id']).first()

		obj, created = Action.objects.get_or_create(
				date=action_json['date'],
				classification=action_json['classification'],
				description=action_json['description'],
				organization=org,
				bill=bill,
			)

		if created:
			print '      adding action: %s' %action_json['description']
		else:
			print '      action already exists'

	def grab_person_memberships(self, person_id):
		# this grabs a person and all their memberships

		url = base_url+'/'+person_id
		r = requests.get(url)
		page_json = json.loads(r.text)

		# TO DO: handle updating people & memberships
		person = Person.objects.filter(ocd_id=person_id).first()
		if not person:
			person = Person.objects.create(
				ocd_id = page_json['id'],
				name = page_json['name'],
				headshot = page_json['image'],
				source_url = page_json['sources'][0]['url'],
				source_note = page_json['sources'][0]['note']
			)
			print '      adding person: %s' % person.name
		else:
			print '      person already exists'

		for membership_json in page_json['memberships']:

			if membership_json['post']:
				post = Post.objects.filter(ocd_id=membership_json['post']['id']).first()
			else:
				post = None

			organization = Organization.objects.filter(ocd_id=membership_json['organization']['id']).first()

			try:
				end_date = parse_date(membership_json['end_date'])
			except:
				end_date = None
			try:
				start_date = parse_date(membership_json['start_date'])
			except:
				start_date = None

			obj, created = Membership.objects.get_or_create(
					organization = organization,
					person = person,
					post = post,
					label = membership_json['label'],
					role = membership_json['role'],
					start_date = start_date,
					end_date = end_date
				)

			if created:
				print '      adding membership: %s' % obj.role
			else:
				print '      membership already exists'