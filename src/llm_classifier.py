import requests

class LLMClassifier:

    def build_prompt(self, title, content):
        
        prompt = f""" You are an intelligent assistant that classifies and summarizes websites.
       
    Categories:
    Abortion: Sites with neutral or balanced presentation of the issue.
    Pro Choice: Sites that provide information about or are sponsored by organizations that support legal abortion or offer support to those seeking it.
    Pro Life: Sites that provide information about or are sponsored by organizations that oppose legal abortion or seek increased restriction.
    Adult Material: Parent category for adult oriented content.
    Adult Content: Sites that display full or partial nudity in a sexual context but not sexual activity.
    Nudity: Sites that offer depictions of nude or seminude human forms.
    Sex: Sites that depict or graphically describe sexual acts or activity including exhibitionism.
    Sex Education: Sites that offer educational information about sex and sexuality.
    Lingerie and Swimsuit: Sites with models in lingerie or swimsuits , including for sale.
    Advocacy Groups:Sites that promote change or reform in public policy , public opinion , social practice , economic activities.
    Bandwidth:Parent category for bandwidth intensive content.
    Educational Video: Sites that host videos with academic/instructional content.
    Entertainment Video: Entertainment oriented video hosting sites.
    Internet Radio and TV: Sites providing Internet radio or TV programming.
    Internet Telephony: Sites enabling VoIP or VoIP software.
    Peer to Peer File Sharing: Sites offering P2P file sharing client software.
    Personal Network Storage and Backup: Sites for personal file backup/exchange in the cloud.
    Streaming Media: Sites that enable streaming media content.
    Surveillance: Sites for real time monitoring via webcams/cameras.
    Viral Video: Sites that host viral/popular videos.
    Business and Economy:Sites sponsored by firms , associations , industry groups or general business.
    Financial Data and Services: Sites providing financial services or market data.
    Education: Educational content parent category.
    Information Technology:Parent category for IT related content.
    Cultural Institutions: Sites for museums , libraries , heritage , etc.
    Educational Institutions: Sites for schools , universities , etc.
    Proxy Avoidance: Sites that bypass web filters via proxy.
    Search Engines and Portals: General search engines and portals.
    Web Hosting: Sites offering hosting services.
    Hacking: Sites related to hacking techniques/tools.
    News and Media:Parent category for news and media content.
    Alternative Journals: Non-mainstream news/journal sites.
    Religion:Parent category for religious content.
    Non Traditional Religions: Websites about new or less common religions.
    Traditional Religions: Sites covering major world religions.
    Socicety and Lifestyle:Parent category for society and lifestyle content.
    Restaurants and Dining: Sites about restaurants , recipes , food culture.
    Gay or Lesbian or Bisexual Interest: LGBTQ+ interest sites.
    Personals and Dating: Dating and personal ads.
    Alcohol and Tobacco: Sites promoting/marketing alcohol or tobacco.
    Drugs:Parent category for drug related content.
    Abused Drugs: Discussion or remedies for illegal , illicit , or abused drugs.
    Prescribed Medications: Information about prescription medications.
    Nutrition: Sites promoting nutritional supplements or diet info.

    Rules for summary:
    - Do NOT mention company or platform names (e.g., Amazon, Wikipedia, Udemy, Coursera).
    - Focus only on the content topic, not the source or brand.

    Rules about classification : 
    -Based on the website’s title, content, and the summary you wrote, you MUST choose exactly ONE category from the provided list.
    -Do not say any category which is not in provided list. Choose closest category.
 
    Website details:
    Title: {title}
    Content: {content[:1000]}

    Respond in the following format:
    Category: <ChosenCategory>
    Summary: <Short summary about the website>
    """
        return prompt

    def classify_text(self, title, content):
        prompt = self.build_prompt(title, content)
        print("Sending prompt to LLM:\n", prompt)  # Burada prompt'u yazdırıyoruz

        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=15
            )
            response.raise_for_status()
            result_text = response.json().get("response", "").strip()
            
            # Satır satır ayır
            lines = result_text.splitlines()
            category = ""
            summary = ""
            #print
            
            print("LLM response:\n", result_text)  # Buraya ekledik
            
            
            
            #print
            for line in lines:
                if line.lower().startswith("category:"):
                    category = line.split(":", 1)[1].strip()
                elif line.lower().startswith("summary:"):
                    summary = line.split(":", 1)[1].strip()

            # Eğer hâlâ unknown'sa, detayları raise et
            if category == "Unknown":
                raise ValueError(f"Model failed to classify. Full response:\n{result_text}")

            return {
                "category": category,
                "summary": summary
            }

        except Exception as e:
            print(f"LLM classification error: {e}")
            return {
                "category": "Unknown",
                "summary": ""
            }
    def is_llm_available(self):
        try:
            import requests
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3", "prompt": "Test", "stream": False},
                timeout=5
            )
            if response.status_code == 200 and "response" in response.json():
                return True
        except Exception:
            pass
        return False
    
