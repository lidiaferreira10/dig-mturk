package mturk;

import java.io.BufferedReader;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.ObjectOutputStream;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;

import org.apache.axis.encoding.Base64;
import org.apache.commons.codec.digest.DigestUtils;
import org.json.JSONArray;
import org.json.JSONObject;

import com.amazonaws.auth.profile.ProfileCredentialsProvider;
import com.amazonaws.mturk.addon.BatchItemCallback;
import com.amazonaws.mturk.addon.HITDataBuffer;
import com.amazonaws.mturk.addon.HITDataCSVReader;
import com.amazonaws.mturk.addon.HITDataInput;
import com.amazonaws.mturk.addon.HITResults;
import com.amazonaws.mturk.requester.Assignment;
import com.amazonaws.mturk.service.axis.RequesterService;
import com.amazonaws.mturk.util.PropertiesClientConfig;
import com.amazonaws.services.s3.AmazonS3;
import com.amazonaws.services.s3.AmazonS3Client;
import com.amazonaws.services.s3.model.Bucket;
import com.amazonaws.services.s3.model.GetObjectRequest;
import com.amazonaws.services.s3.model.ListObjectsRequest;
import com.amazonaws.services.s3.model.ObjectListing;
import com.amazonaws.services.s3.model.ObjectMetadata;
import com.amazonaws.services.s3.model.PutObjectRequest;
import com.amazonaws.services.s3.model.S3Object;
import com.amazonaws.services.s3.model.S3ObjectSummary;

public class hitResults {
	private RequesterService service;
	String successFile = "", fileContent = "";
	private String bucketName = "", prefixKey = "";
	private AmazonS3 s3client;

	public hitResults(String bucketName) {
		service = new RequesterService(new PropertiesClientConfig(
				"mturk_sandbox.properties"));
		this.bucketName = "aisoftwareresearch/ner/" + bucketName + "/hits";
		this.prefixKey = "ner/" + bucketName + "/hits";
		s3client = new AmazonS3Client(new ProfileCredentialsProvider());
		s3client.setEndpoint("s3-us-west-2.amazonaws.com");
	}

	public void getAllHits() {
		ArrayList<String> hitIds = new ArrayList<String>();
		ArrayList<String> folderNames = new ArrayList<String>();
		BufferedReader br = null;
		String line, cvsSplitBy = "\t";
		String mainBucket = "aisoftwareresearch";
		try {
			ListObjectsRequest listObjectsRequest = new ListObjectsRequest()
					.withBucketName(mainBucket).withPrefix(prefixKey);
			ObjectListing objectListing;
			do {
				objectListing = s3client.listObjects(listObjectsRequest);
				/*
				 * identify the sub folder names in the specified bucket. Store
				 * the sub folder names inside a separate array. This is done so
				 * that the files required for a particular hit aren't mixed up
				 * with data from another hit instance.
				 */
				for (S3ObjectSummary objectSummary : objectListing
						.getObjectSummaries()) {
					String key = objectSummary.getKey();
					if (!key.equalsIgnoreCase(prefixKey)) {
						key = key.substring((prefixKey + "/").length());

						if (key.indexOf('/') > -1) {
							String[] keyParts = key.split("/");
							if (keyParts.length == 1) {
								folderNames.add(keyParts[0]);
							}
						}
					}
				}
				listObjectsRequest.setMarker(objectListing.getNextMarker());
			} while (objectListing.isTruncated());

			Iterator<String> folderIter = folderNames.iterator();
			while (folderIter.hasNext()) {
				String currFileName = folderIter.next();
				successFile = currFileName + "/" + currFileName + ".success";
				S3Object in_object = s3client.getObject(new GetObjectRequest(
						bucketName, successFile));
				InputStream in_objectData = in_object.getObjectContent();
				BufferedReader in_reader = new BufferedReader(
						new InputStreamReader(in_objectData));
				while ((line = in_reader.readLine()) != null) {
					String[] content = line.split(cvsSplitBy);
					content[0] = content[0].replace("\"", "");
					if (!content[0].equalsIgnoreCase("hitid")) {
						hitIds.add(content[0]);
					}
				}
			}
			approveAssignments(hitIds);
		} catch (Exception e) {
			System.err.println(e.getMessage());
		}
	}

	public void approveAssignments(ArrayList<String> hitIds) {
		Assignment[] assignment = null;
		String defaultFeedback = "default feedback";
		try {
			if (hitIds == null) {
				throw new Exception("No hits found");
			} else {
				Iterator<String> iterator = hitIds.iterator();
				while (iterator.hasNext()) {
					assignment = service
							.getAllSubmittedAssignmentsForHIT(iterator.next()
									.toString());
					if (assignment == null) {
						throw new Exception("No assignments found");
					} else {
						System.out.println("Number of assignments --- "
								+ assignment.length);
						String[] assignmentIds = new String[assignment.length];
						String[] requesterFeedback = new String[assignment.length];
						for (int j = 0; j < assignment.length; j++) {
							requesterFeedback[j] = "approved via java api";
							assignmentIds[j] = assignment[j].getAssignmentId()
									.toString();
						}
						System.out
								.println("approving all assignments for current hit");
						service.approveAssignments(assignmentIds,
								requesterFeedback, defaultFeedback,
								new BatchItemCallback() {
									public void processItemResult(
											Object itemId, boolean succeeded,
											Object result,
											Exception itemException) {
										System.out.println("approved result");
										System.out.println("Item id ---"
												+ itemId);
										System.out.println("success bool ---"
												+ succeeded);
										System.out.println(result);
									}
								});

					}
				}
			}
			getResults();
		} catch (Exception e) {

		}
	}

	public void getResults() {
		String content = "";
		ArrayList<String> folderNames = new ArrayList<String>();
		String mainBucket = "aisoftwareresearch";
		try {
			ListObjectsRequest listObjectsRequest = new ListObjectsRequest()
					.withBucketName(mainBucket).withPrefix(prefixKey);
			ObjectListing objectListing;
			do {
				objectListing = s3client.listObjects(listObjectsRequest);
				/*
				 * identify the sub folder names in the specified bucket. Store
				 * the sub folder names inside a separate array. This is done so
				 * that the files required for a particular hit aren't mixed up
				 * with data from another hit instance.
				 */
				for (S3ObjectSummary objectSummary : objectListing
						.getObjectSummaries()) {
					String key = objectSummary.getKey();
					if (!key.equalsIgnoreCase(prefixKey)) {
						key = key.substring((prefixKey + "/").length());

						if (key.indexOf('/') > -1) {
							String[] keyParts = key.split("/");
							if (keyParts.length == 1) {
								folderNames.add(keyParts[0]);
							}
						}
					}
				}
				listObjectsRequest.setMarker(objectListing.getNextMarker());
			} while (objectListing.isTruncated());

			Iterator<String> folderIter = folderNames.iterator();
			while (folderIter.hasNext()) {
				String currFileName = folderIter.next();
				successFile = currFileName + "/" + currFileName + ".success";
				HITDataBuffer input_buffer = new HITDataBuffer();
				S3Object in_object = s3client.getObject(new GetObjectRequest(
						bucketName, successFile));
				System.out.println(in_object.getRedirectLocation());
				InputStream in_objectData = in_object.getObjectContent();
				BufferedReader in_reader = new BufferedReader(
						new InputStreamReader(in_objectData));
				while ((content = in_reader.readLine()) != null) {
					input_buffer.writeLine(content.split("\t"));
				}
				HITDataInput input = new HITDataCSVReader(
						"src\\mturk\\ner.success");
				// in_object.close();
				// in_objectData.close();
				// in_reader.close();
				/* Reset the content for each success file */
				fileContent = "";
				service.getResults(input, new BatchItemCallback() {
					public void processItemResult(Object itemId,
							boolean succeeded, Object result,
							Exception itemException) {
						// System.out.println(result);
						HITResults hitresult = (HITResults) result;
						// System.out.println(hitresult);
						Assignment resultassignments[] = hitresult
								.getAssignments();
						// System.out.println("here");
						Map<String, String> assignmap, hitmap, resultmap;
						resultmap = new HashMap<String, String>();
						// System.out.println(resultassignments.length);
						for (int j = 0; j < resultassignments.length; j++) {

							hitmap = hitresult.getHITResults();
							assignmap = hitresult
									.getAssignmentResults(resultassignments[j]);
							resultmap.putAll(hitmap);
							resultmap.putAll(assignmap);
							String workerId = resultmap.get("workerid");
							String assignmentid = resultmap.get("assignmentid");
							String hitid = resultmap.get("hitid");
							String[] allAnswers = resultmap.get(
									"answers[question_id answer_value]").split(
									"\n");
							for (String answer : allAnswers) {
								answer = answer.trim();
								String trimValue = answer.split("\t")[0];
								fileContent += hitid
										+ "\t"
										+ workerId
										+ "\t"
										+ assignmentid
										+ "\t"
										+ answer.substring(trimValue.length())
												.trim() + "\n";
							}
							resultmap.clear();
						}
					}
				});
				String keyName = currFileName + "/" + currFileName + ".tsv";
				InputStream inputStream = new ByteArrayInputStream(
						fileContent.getBytes());
				ObjectMetadata metadata = new ObjectMetadata();
				/*
				 * Set content length. Else stream contents will be buffered in
				 * memory and could result in out of memory errors.
				 */
				metadata.setContentLength(fileContent.length());
				PutObjectRequest request = new PutObjectRequest(bucketName,
						keyName, inputStream, metadata);
				s3client.putObject(request);
			}
		} catch (Exception e) {
			System.err.println(e.getMessage());
		}
	}

	public static void main(String args[]) {
		if (args[0] == null) {
			System.out.println();
		} else {
			hitResults hitResults = new hitResults(args[0]);
			hitResults.getAllHits();
		}
	}
}
