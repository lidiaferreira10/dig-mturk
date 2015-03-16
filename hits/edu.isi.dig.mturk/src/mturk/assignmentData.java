package mturk;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.ObjectOutputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Iterator;
import java.util.Map;

import org.json.JSONArray;
import org.json.JSONObject;

import com.amazonaws.mturk.addon.BatchItemCallback;
import com.amazonaws.mturk.addon.HITDataCSVReader;
import com.amazonaws.mturk.addon.HITDataInput;
import com.amazonaws.mturk.addon.HITResults;
import com.amazonaws.mturk.requester.Assignment;
import com.amazonaws.mturk.service.axis.RequesterService;
import com.amazonaws.mturk.util.PropertiesClientConfig;

public class assignmentData {
	private RequesterService service;

	public assignmentData() {
		service = new RequesterService(new PropertiesClientConfig(
				"mturk.properties"));
	}

	public void getAllHits() {
		ArrayList<String> hitIds = new ArrayList<String>();
		BufferedReader br = null;
		String line, cvsSplitBy = "\t";
		assignmentData obj = new assignmentData();
		try {
			File[] folders = new File("D:\\mturk\\NER\\").listFiles();
			for (File dir : folders) {
				if (dir.isDirectory()) {
					File[] files = dir.listFiles();
					for (File file : files) {
						String filename = file.getName();
						String extension = filename.substring(
								filename.lastIndexOf(".") + 1,
								filename.length());
						if (extension.equalsIgnoreCase("success")) {
							br = new BufferedReader(new FileReader(file));
							while ((line = br.readLine()) != null) {
								String[] content = line.split(cvsSplitBy);
								content[0] = content[0].replace("\"", "");
								if (!content[0].equalsIgnoreCase("hitid")) {
									hitIds.add(content[0]);
									System.out.println(content[0]);
								}
							}
						}

					}
				}
			}

			obj.approveAssignments(hitIds);
		} catch (Exception e) {

		}
	}

	public void approveAssignments(ArrayList<String> hitIds) {
		Assignment[] assignment = null;
		String defaultFeedback = "default feedback";
		assignmentData obj = new assignmentData();
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
			obj.getResults();
		} catch (Exception e) {

		}
	}

	public void getResults() {
		String inputFile = "";

		try {
			File[] folders = new File("D:\\mturk\\NER\\").listFiles();
			final JSONArray resultarray = new JSONArray();
			for (File dir : folders) {
				if (dir.isDirectory()) {
					File[] files = dir.listFiles();
					for (File file : files) {
						String filename = file.getName();
						String extension = filename.substring(
								filename.lastIndexOf(".") + 1,
								filename.length());
						if (extension.equalsIgnoreCase("success")) {
							inputFile = file.getAbsolutePath();
							HITDataInput input = new HITDataCSVReader(inputFile);
							service.getResults(input, new BatchItemCallback() {
								public void processItemResult(Object itemId,
										boolean succeeded, Object result,
										Exception itemException) {
									HITResults hitresult = (HITResults) result;
									Assignment resultassignments[] = hitresult
											.getAssignments();
									Map<String, String> assignmap, hitmap, resultmap;
									resultmap = new HashMap<String, String>();
									for (int j = 0; j < resultassignments.length; j++) {

										hitmap = hitresult.getHITResults();
										assignmap = hitresult
												.getAssignmentResults(resultassignments[j]);

										resultmap.putAll(hitmap);
										resultmap.putAll(assignmap);
										resultarray.put(resultmap);
										JSONObject resultjson = new JSONObject(
												resultmap);
										System.out.println(resultjson
												.toString());

										resultmap.clear();
									}
								}
							});
						}

					}
				}
			}
			try {
				final ObjectOutputStream outputStream = new ObjectOutputStream(
						new FileOutputStream("src\\mturk\\results.txt"));
				outputStream.writeObject(resultarray.toString());
				outputStream.flush();
				outputStream.close();
			} catch (Exception e) {
				System.err.println("Error: " + e);
			}

		} catch (Exception e) {
			System.err.println(e.getMessage());
			System.err.println(e.getLocalizedMessage());
		}
	}

	public static void main(String args[]) {
		assignmentData obj = new assignmentData();
		obj.getAllHits();
	}
}
