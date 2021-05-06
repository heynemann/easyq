.PHONY: worker api

api:
	uvicorn newlane:app --reload

worker:
	export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES \
		&& rq worker -v
