IMAGE ?= splitpub:latest
IN ?= book.epub
OUTDIR ?= outdir
IGNORE ?= .splitpub-ignore

.PHONY: help build check split-tar split-dir validate clean

help:
	@echo "Targets:"
	@echo "  build       - Build Docker image ($(IMAGE))"
	@echo "  check       - Check TOC (JSON) via stdin"
	@echo "  split-tar   - Split to tar stream > out.tar"
	@echo "  split-dir   - Split to mounted $(OUTDIR) directory"
	@echo "  validate    - Validate out.tar (from split-tar)"
	@echo "Variables: IMAGE, IN, OUTDIR, IGNORE"

build:
	docker build -t $(IMAGE) .

check: build
	docker run --rm -i $(IMAGE) --mode check --format json < $(IN)

split-tar: build
	docker run --rm -i $(IMAGE) --mode split < $(IN) > out.tar
	@echo "Wrote out.tar"

split-dir: build
	mkdir -p $(OUTDIR)
	docker run --rm -i \
	  -v "$(PWD)":/work -w /work \
	  -v "$(PWD)/$(OUTDIR)":/out \
	  $(IMAGE) --mode split --out /out --ignore-file /work/$(IGNORE) < $(IN)
	@echo "Wrote EPUBs to $(OUTDIR)"

validate:
	python3 cli.py --mode validate --input out.tar

clean:
	rm -f out.tar
	rm -rf $(OUTDIR)
