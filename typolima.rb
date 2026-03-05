# Homebrew Formula template for TypoLima.
# Copy this to your homebrew-tap repository as Formula/typolima.rb

class Typolima < Formula
  include Language::Python::Virtualenv

  desc "Conservative typographic fixer for HTML, PHP and text"
  homepage "https://github.com/heptau/typolima"
  # You should update this URL and SHA256 whenever you release a new version
  url "https://github.com/heptau/typolima/archive/refs/tags/v0.2.0.tar.gz"
  sha256 "REPLACE_WITH_ACTUAL_SHA256"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    # Simple test to verify the binary runs
    assert_match "usage: typolima", shell_output("#{bin}/typolima --help")
  end
end
