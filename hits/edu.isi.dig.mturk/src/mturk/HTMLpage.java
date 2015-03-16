package mturk;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.PrintStream;
import java.security.MessageDigest;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;

import com.amazonaws.AmazonClientException;
import com.amazonaws.AmazonServiceException;
import com.amazonaws.auth.profile.ProfileCredentialsProvider;
import com.amazonaws.mturk.addon.HITDataCSVWriter;
import com.amazonaws.mturk.addon.HITDataOutput;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3Client;
import com.amazonaws.services.s3.model.GetObjectRequest;
import com.amazonaws.services.s3.model.ObjectMetadata;
import com.amazonaws.services.s3.model.PutObjectRequest;
import com.amazonaws.services.s3.model.S3Object;

public class HTMLpage {

	private PrintStream printhtml;
	/*
	 * bucketName: path where all files all stored in s3. AWS Credentials :
	 * access tokens acquired from AWS
	 */
	private String bucketName = "", JSONkey = "";
	private AmazonS3 s3client;

	public static void main(String[] args) {
		HTMLpage htmlpage = new HTMLpage(args[1], args[3]);
		nerHit hit = new nerHit(args[1]);
		htmlpage.parseJSON(args[1]);
		if (hit.hasEnoughFund()) {
			hit.getFolders();
		}

	}

	HTMLpage(String bucketName, String JSONkey) {
		this.bucketName = "aisoftwareresearch/ner/" + bucketName;
		this.JSONkey = JSONkey;
		s3client = new AmazonS3Client(new ProfileCredentialsProvider());
	}

	/*
	 * parse the json file in s3. create all components(html file, input file,
	 * properties file, question file) required to create a hit.
	 */
	public void parseJSON(String S3FolderName) {
		JSONParser parser = new JSONParser();
		String category = new String(), instructions, title;
		Map<String, String> sentences = new HashMap<String, String>();
		String filename = "", scratch_categories = "";

		try {
			s3client.setEndpoint("s3-us-west-2.amazonaws.com");
			System.out.println(bucketName + "      fdfsdfsdfsd        "
					+ JSONkey);
			S3Object object = s3client.getObject(new GetObjectRequest(
					bucketName, JSONkey));
			InputStream objectData = object.getObjectContent();
			BufferedReader reader = new BufferedReader(new InputStreamReader(
					objectData));
			Object obj = parser.parse(reader);
			JSONArray array = (JSONArray) obj;
			for (Object o : array) {
				JSONObject jsonObject = (JSONObject) o;
				category = "";
				instructions = (String) jsonObject.get("instructions_html");
				title = (String) jsonObject.get("title");
				JSONArray categories = (JSONArray) jsonObject.get("categories");
				scratch_categories = jsonObject.get("scratch_categories")
						.toString();
				Iterator<?> categoryIter = categories.iterator();
				while (categoryIter.hasNext()) {
					JSONObject innerObj = (JSONObject) categoryIter.next();
					category += innerObj.get("label") + ",";

				}
				/* remove last added comma from category */
				if (category.length() > 0
						&& category.charAt(category.length() - 1) == ',') {
					category = category.substring(0, category.length() - 1);
				}
				JSONArray sent = (JSONArray) jsonObject.get("hit_sentences");
				Iterator<?> sentIter = sent.iterator();
				while (sentIter.hasNext()) {
					JSONObject innerObj = (JSONObject) sentIter.next();
					sentences.put(innerObj.get("id").toString(),
							innerObj.get("sentence").toString());
				}

				filename = calculateSHA(jsonObject);
				createFolder(filename);
				generateHTML(title, instructions, category, sentences,
						filename, scratch_categories);
				createInputFile(sentences, filename);
				createPropertiesFile(jsonObject, filename, sentences);
				createQuestionFile(filename, S3FolderName);
				sentences.clear();

			}
			objectData.close();
		} catch (Exception e) {
			System.err.println("Parser" + e.getLocalizedMessage());
		}

	}

	/*
	 * Compute SHA for the contents of the JSON object. Input: JSON object
	 * output: SHA in hex format
	 */
	public String calculateSHA(JSONObject jsonObject) {
		String filename = "";
		try {
			MessageDigest digest = MessageDigest.getInstance("SHA-1");
			digest.reset();
			digest.update(jsonObject.toString().getBytes("UTF-8"));
			byte[] mdbytes = digest.digest();
			StringBuffer sb = new StringBuffer("");
			for (int i = 0; i < mdbytes.length; i++) {
				sb.append(Integer.toString((mdbytes[i] & 0xff) + 0x100, 16)
						.substring(1));
			}
			filename = sb.toString();

		} catch (Exception e) {
			System.err.println("SHA" + e.getLocalizedMessage());
		}
		return filename;
	}

	/*
	 * Creating a folder in S3. The folder will be created inside the Bucketname
	 * specified
	 */
	public void createFolder(String folderName) {
		ObjectMetadata metadata = new ObjectMetadata();
		metadata.setContentLength(0);
		/* Create empty content */
		InputStream emptyContent = new ByteArrayInputStream(new byte[0]);

		try {
			/* Create a PutObjectRequest passing the folder name suffixed by /. */
			PutObjectRequest putObjectRequest = new PutObjectRequest(
					bucketName, folderName + "/", emptyContent, metadata);
			s3client.putObject(putObjectRequest);
			System.out.println("createf folder->" + bucketName + "->"
					+ folderName);
		} catch (Exception e) {
			System.err.println(e.getMessage());
		}
	}

	public void generateHTML(String title, String instructions,
			String categories, Map<String, String> sentences, String filename,
			String scratch_categories) {
		int linenum = 1;
		try {
			OutputStream htmlfile = new FileOutputStream(new File(
					"src/mturk/ner.html"));
			PrintStream printhtml = new PrintStream(htmlfile);

			String htmlheader = "<html><head>";
			htmlheader += "<script src=\"https://ajax.googleapis.com/ajax/libs/jquery/1.11.2/jquery.min.js\"></script>";
			htmlheader += "<script src = \"https://s3-us-west-2.amazonaws.com/aisoftwareresearch/ner_html/ner.js\"> </script>";
			htmlheader += "<script src = \"https://maxcdn.bootstrapcdn.com/bootstrap/3.2.0/js/bootstrap.min.js\"> </script>";
			htmlheader += "<link rel=\"stylesheet\" type=\"text/css\" href=\"https://s3-us-west-2.amazonaws.com/aisoftwareresearch/ner_html/ner.css\">";
			htmlheader += "<link rel=\"stylesheet\" type=\"text/css\" href=\"https://maxcdn.bootstrapcdn.com/bootstrap/3.3.2/css/bootstrap.min.css\">";
			htmlheader += "</head><body categories= \"" + categories + "\">";
			/*
			 * form submit URL should point to MTurk sandbox / MTurk URL. Sanbox
			 * URL: https://workersandbox.mturk.com/mturk/externalSubmit. MTurk
			 * URL: http://www.mturk.com/mturk/externalSubmit. Assignment Id as
			 * a hidden parameter to pass the hit id while submitting data.
			 */
			htmlheader += "<form id=\"mturk_form\" method=\"POST\" action=\"https://workersandbox.mturk.com/mturk/externalSubmit\"><input type=\"hidden\" id=\"assignmentId\" name=\"assignmentId\" value=\"\">";
			htmlheader += "<div class=\"page-header\">	<h1>" + title
					+ "</h1>	</div>";
			htmlheader += instructions;

			String htmlfooter = "<div class=\"btn_wrapper\">	<button name='submit' class=\"submitBtn btn btn-primary\"> Submit</button>	</div>";
			htmlfooter += "<div class=\"modal fade\" id=\"modal_box\">	<div class=\"modal-dialog\">	<div class=\"modal-content\">";
			htmlfooter += "<div class=\"modal-header alert alert-danger modal_title_custom\">	<button type=\"button\" class=\"close\" data-dismiss=\"modal\" aria-label=\"Close\">";
			htmlfooter += "<span aria-hidden=\"true\">&times;</span></button>	<h4 class=\"modal-title\">Invalid Submission</h4></div><div class=\"modal-body\" id=\"modal-body-text\">";
			htmlfooter += "	<p> The reasons for invalid submission are <li> Every sentence should have either no entity checked or should have atleast one identified entity. </li>  <li> Each highlighted entity should be categorized.</li> </p>	</div>	";
			htmlfooter += "<div class=\"modal-footer\">	<button type=\"button\" class=\"btn btn-default\" data-dismiss=\"modal\">OK</button>";
			htmlfooter += "</div> </div> </div> </div>";
			htmlfooter += "</form> </body></html>";

			printhtml.println(htmlheader);

			Iterator<?> sentIter = sentences.entrySet().iterator();
			while (sentIter.hasNext()) {
				@SuppressWarnings("rawtypes")
				Map.Entry pair = (Map.Entry) sentIter.next();
				printhtml.println(createPanel(linenum, pair.getValue()
						.toString(), scratch_categories));
				linenum++;
			}
			printhtml.println(htmlfooter);
			printhtml.close();
			htmlfile.close();
			uploadFile(filename, "html");
		} catch (Exception e) {
			System.err.println("HTML " + e.getLocalizedMessage());
		}
	}

	/*
	 * creates a panel for each sentence. Input: linenum - to keep track of
	 * sentence number; sentence - the text content of sentence;
	 * scratch_categories: the check boxes shown at the bottom of each sentence
	 * panel. It usually contains "no entity present" Output: String containing
	 * HTML mark up for the panel
	 */
	public String createPanel(int linenum, String sentence,
			String scratch_categories) {

		String panelHTML = "<div class=\"panel panel-primary\" name=\"parent_container\">";
		panelHTML += "<div class=\"panel-body\" id=\"container_" + linenum
				+ "\">	<div class=\"sentence\" id=\"sentence_" + linenum
				+ "\"> " + sentence + "</div> </div>";
		if (scratch_categories.length() > 0)
			panelHTML += "<div class=\"checkbox custom_checkbox\"><label> <input type=\"checkbox\">"
					+ scratch_categories + "</label> </div></div>";
		return panelHTML;
	}

	/*
	 * creates the .input file. This file contains the id of each sentence. The
	 * ids are separated by "/". Input : sentences - hash map containing id and
	 * text content for all sentences in current JSON Object; filename - SHA of
	 * JSON content. Used to uniquely identify data in each hit.
	 */
	public void createInputFile(Map<String, String> sentences, String filename) {

		int size = sentences.size();
		char separator = '\\';
		String[] annotations = new String[size];
		String[] newLine = { "\n" };
		int linenum = 0;
		try {

			String inputFile = "src/mturk/ner.input";
			HITDataOutput inputEditor = new HITDataCSVWriter(inputFile,
					separator, false, false);
			@SuppressWarnings("rawtypes")
			Iterator sentIter = sentences.entrySet().iterator();
			while (sentIter.hasNext()) {
				@SuppressWarnings("rawtypes")
				Map.Entry pair = (Map.Entry) sentIter.next();
				annotations[linenum] = pair.getKey().toString();
				linenum++;
			}
			inputEditor.setFieldNames(annotations);
			inputEditor.setFieldNames(annotations);
			inputEditor.setFieldNames(newLine);
			uploadFile(filename, "input");
		} catch (Exception e) {
			System.err.println("input file" + e.getLocalizedMessage());
		}
	}

	/*
	 * creates properties file. It contains all the specifications for a
	 * particular hit. Input: jsonObject - current JSON object; filename - SHA
	 * of JSON object; sentences - needed here to create annotations. The
	 * annotations should match values in input file.
	 */
	public void createPropertiesFile(JSONObject jsonObject, String filename,
			Map<String, String> sentences) {
		String annotations = new String();
		try {
			OutputStream propFile = new FileOutputStream(new File(
					"src/mturk/ner.properties"));
			PrintStream printhtml = new PrintStream(propFile);
			if (jsonObject.get("title").toString().length() > 0)
				printhtml
						.println("title:" + jsonObject.get("title").toString());
			if (jsonObject.get("description").toString().length() > 0)
				printhtml.println("description:"
						+ jsonObject.get("description").toString());
			if (jsonObject.get("keywords").toString().length() > 0)
				printhtml.println("keywords:"
						+ jsonObject.get("keywords").toString());
			if (jsonObject.get("reward").toString().length() > 0)
				printhtml.println("reward:"
						+ Float.valueOf(jsonObject.get("reward").toString()));
			if (jsonObject.get("num_assignments").toString().length() > 0)
				printhtml.println("assignments:"
						+ Integer.parseInt(jsonObject.get("num_assignments")
								.toString()));
			Iterator<?> sentIter = sentences.entrySet().iterator();
			while (sentIter.hasNext()) {
				@SuppressWarnings("rawtypes")
				Map.Entry pair = (Map.Entry) sentIter.next();
				annotations += "${" + pair.getKey().toString() + "},";
			}

			/* remove last added comma from annotation */
			if (annotations.length() > 0
					&& annotations.charAt(annotations.length() - 1) == ',') {
				annotations = annotations
						.substring(0, annotations.length() - 1);
			}
			if (annotations.length() > 0)
				printhtml.println("annotations:" + annotations);
			if (jsonObject.get("assignment_duration").toString().length() > 0)
				printhtml.println("assignmentduration:"
						+ Integer.parseInt(jsonObject
								.get("assignment_duration").toString()));
			if (jsonObject.get("hit_lifetime").toString().length() > 0)
				printhtml.println("hitlifetime:"
						+ Integer.parseInt(jsonObject.get("hit_lifetime")
								.toString()));
			if (jsonObject.get("autoapproval").toString().length() > 0)
				printhtml.println("autoapprovaldelay:"
						+ Integer.parseInt(jsonObject.get("autoapproval")
								.toString())); /* units - days */

			/*
			 * Qualifications to filter turkers who match our specifications.
			 * The input file may contain more than one qualification.
			 */
			JSONArray qualifications = (JSONArray) jsonObject
					.get("qualifications");
			int qualificationCount = 1;
			Iterator<?> qualIter = qualifications.iterator();
			while (qualIter.hasNext()) {

				JSONObject innerObj = (JSONObject) qualIter.next();

				if (innerObj.get("id").toString().length() > 0) {
					printhtml.println("qualification." + qualificationCount
							+ ":"
							+ Integer.parseInt(innerObj.get("id").toString()));
					printhtml.println("qualification.comparator."
							+ qualificationCount + ":"
							+ innerObj.get("comparator").toString());
					printhtml
							.println("qualification.value."
									+ qualificationCount
									+ ":"
									+ Integer.parseInt(innerObj.get("value")
											.toString()));
					printhtml.println("qualification.private."
							+ qualificationCount
							+ ":"
							+ Boolean.getBoolean(innerObj.get("private")
									.toString()));
					qualificationCount++;
				}

			}
			printhtml.close();
			propFile.close();
			uploadFile(filename, "properties");
		} catch (Exception e) {
			System.err.println("Properties" + e.getLocalizedMessage());
		}
	}

	/*
	 * creates question file. The question file match a XML format pre defined
	 * by amazon. The ExternalURL tag should point to the HTML file that is
	 * hosted in S3.
	 */
	public void createQuestionFile(String filename, String S3FolderName) {
		try {
			OutputStream quesFile = new FileOutputStream(new File(
					"src/mturk/ner.question"));
			printhtml = new PrintStream(quesFile);
			printhtml.println("<?xml version=\"1.0\"?>");
			printhtml
					.println("<ExternalQuestion xmlns=\"http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2006-07-14/ExternalQuestion.xsd\">");
			printhtml
					.println("<ExternalURL>https://aisoftwareresearch.s3.amazonaws.com/ner/"
							+ S3FolderName
							+ "/"
							+ filename
							+ "/"
							+ filename
							+ ".html</ExternalURL>	");
			printhtml.println("<FrameHeight>600</FrameHeight>");
			printhtml.println("</ExternalQuestion>");
			uploadFile(filename, "question");
		} catch (Exception e) {
			System.err.println("Question" + e.getLocalizedMessage());
		}

	}

	/*
	 * upload file to S3. Each file is put inside a folder. Folder Name is SHA
	 * of JSON
	 */
	public void uploadFile(String filename, String fileType) {
		String keyName = filename + "/" + filename + "." + fileType;
		String uploadFileName = "src\\mturk\\ner." + fileType;
		try {
			File file = new File(uploadFileName);
			s3client.putObject(new PutObjectRequest(bucketName, keyName, file));
			System.out.println("uploaded:: " + fileType);
		} catch (AmazonServiceException ase) {
			System.out.println("Error Message:    " + ase.getMessage());
		} catch (AmazonClientException ace) {
			System.out.println("Error Message: " + ace.getMessage());
		}
	}

}